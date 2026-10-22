"""Bounded live evaluation for the Agentic RAG pilot.

Never touches production storage: restores a versioned corpus backup into a
temporary SQLite file and uses the durable operator RequestBudget ledger that
caps real provider requests and reserved tokens across the whole release.
"""
import argparse
import asyncio
import hashlib
import json
import time
import uuid
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from pydantic import SecretStr

from landlaw.agentic_rag import BoundedAgenticRAG
from landlaw.config import Settings
from landlaw.models import ChatRequest
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.provider import GroqProvider, ProviderUnavailable
from landlaw.request_budget import BudgetExceeded
from landlaw.simple_rag import SimpleAnswer
from landlaw.store import RateLimited, Store


class PilotAllocation:
    """Flat conservative reservation: 3,000 tokens per provider request.

    This is the same approved pattern used by the previous Simple RAG live
    allocation. Actual provider usage is recorded after the response; a single
    response above its reservation blocks every later request instead of
    silently continuing under an unsafe estimate.
    """

    def __init__(self, path, identity, *, max_requests=20, max_tokens=60000, per_request=3000):
        self.path = Path(path)
        self.identity, self.max_requests, self.max_tokens, self.per_request = identity, max_requests, max_tokens, per_request
        self.entries, self.actual_tokens, self.blocked_reason = [], 0, None
        if self.path.exists():
            prior = json.loads(self.path.read_text())
            if (prior.get('identity'), prior.get('max_requests'), prior.get('max_tokens'), prior.get('per_request')) != (
                    identity, max_requests, max_tokens, per_request):
                raise ValueError('Pilot allocation identity/limits changed; preserve the prior run')
            self.entries = prior['entries']
            self.actual_tokens = prior['actual_tokens']
            self.blocked_reason = prior.get('blocked_reason')
            self.summary()
        else:
            self.persist()

    def summary(self):
        reserved = sum(entry['reservation'] for entry in self.entries)
        return {
            'max_requests': self.max_requests, 'reserved_token_cap': self.max_tokens,
            'reserved_tokens_per_request': self.per_request, 'requests_reserved': len(self.entries),
            'reserved_tokens': reserved, 'remaining_reserved_tokens': self.max_tokens - reserved,
            'reported_actual_tokens': self.actual_tokens, 'blocked_reason': self.blocked_reason,
            'provider_quota_is_separate': True,
        }

    def persist(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        target = self.path.with_suffix(self.path.suffix + '.pending')
        target.write_text(json.dumps({'version': 1, 'identity': self.identity, 'max_requests': self.max_requests,
                                      'max_tokens': self.max_tokens, 'per_request': self.per_request,
                                      'actual_tokens': self.actual_tokens, 'blocked_reason': self.blocked_reason,
                                      'summary': self.summary(), 'entries': self.entries},
                                     ensure_ascii=False, indent=2) + '\n')
        target.replace(self.path)

    def reserve(self, request):
        if self.blocked_reason:
            raise BudgetExceeded(self.blocked_reason)
        if len(self.entries) >= self.max_requests:
            self.blocked_reason = 'request_cap'
            self.persist()
            raise BudgetExceeded(self.blocked_reason)
        if self.summary()['remaining_reserved_tokens'] < self.per_request:
            self.blocked_reason = 'reserved_token_cap'
            self.persist()
            raise BudgetExceeded(self.blocked_reason)
        ident = len(self.entries)
        self.entries.append({'id': ident, 'state': 'reserved', 'reservation': self.per_request,
                             'wire_bytes': len(json.dumps(request, ensure_ascii=False, separators=(',', ':')).encode()),
                             'confirmed_usage': None})
        self.persist()
        return ident

    def settle(self, ident, usage, *, status_code=None, headers=None):
        entry = self.entries[ident]
        if entry['state'] != 'reserved':
            raise ValueError('Pilot allocation already settled')
        reported = usage.get('total_tokens') if isinstance(usage, dict) else None
        entry['http_status'] = status_code
        if type(reported) is int and reported >= 0:
            entry.update(state='confirmed', confirmed_usage=reported)
            self.actual_tokens += reported
            if reported > self.per_request:
                self.blocked_reason = 'single_request_exceeded_reservation'
            if self.actual_tokens >= self.max_tokens:
                self.blocked_reason = 'reported_actual_token_cap'
        else:
            entry['state'] = 'estimated'
        self.persist()


class DryProvider:
    """No-network provider used only to verify the live runner plumbing."""
    configured = True

    def __init__(self, settings):
        self.settings = settings

    async def embed(self, text, **kwargs):
        budget = kwargs.get('budget')
        if budget is not None:
            budget.embedding_calls += 1
        return []

    async def tool_step(self, instruction, messages, tools, budget, max_attempts=1):
        budget.llm()
        user = messages[-1]['content'] if messages else ''
        if any(term in user.casefold() for term in ('xin chào', 'cảm ơn', 'giúp được gì')):
            return {'content': 'Xin chào, mình hỗ trợ tra cứu pháp luật đất đai Vành đai 4.', 'tool_calls': []}
        return {'content': '', 'tool_calls': [{'id': 'dry-1', 'name': 'search_legal_evidence',
                                               'arguments': json.dumps({'query': user[:200]}, ensure_ascii=False)}]}

    async def generate(self, schema, instruction, payload, budget, max_attempts=1):
        budget.llm()
        context = payload.get('context', '')
        answer = 'Theo nguồn [S1], điều kiện và quy định cần được kiểm tra theo hồ sơ.' if '[S1]' in context \
            else 'Mình chưa tìm thấy đoạn nguồn đã review đủ để trả lời.'
        return SimpleAnswer(answer=answer)

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / 'data/evaluation/agentic-v1-20261022'
LEDGER = ROOT / 'reports/evaluation/agentic-rag-final/request-budget.json'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def load_suite():
    manifest = json.loads((SUITE / 'manifest.json').read_text())
    raw = (SUITE / 'scenarios.jsonl').read_bytes()
    if hashlib.sha256(raw).hexdigest() != manifest['scenarios_sha256']:
        raise SystemExit('Frozen suite hash mismatch')
    cases = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    return manifest, {case['id']: case for case in cases}


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--cases', nargs='*', default=['A01', 'T01', 'T02', 'L01', 'L02', 'L03'])
    parser.add_argument('--backup', default='data/staging/phase2c-current/acceptance-context-pack-backup.json')
    parser.add_argument('--receipts', default='reports/source-review-20261022/receipts-20261022')
    parser.add_argument('--policy-v1', default='reports/source-review-20261022/source-gate-20261022.json')
    parser.add_argument('--policy', default='reports/source-review-20261022/standing/source-gate-v2-candidate-20261022.json')
    parser.add_argument('--output', default='reports/evaluation/agentic-rag-final/pre-deployment-live.json')
    parser.add_argument('--request-cap', type=int, default=16)
    parser.add_argument('--token-cap', type=int, default=48000)
    parser.add_argument('--global-request-cap', type=int, default=20)
    parser.add_argument('--global-token-cap', type=int, default=60000)
    parser.add_argument('--cooldown-seconds', type=int, default=20)
    args = parser.parse_args()
    manifest, cases = load_suite()
    selected = [cases[case_id] for case_id in args.cases]

    load_dotenv(ROOT / '.env')
    base = Settings()
    settings = base.model_copy(update={
        'app_env': 'development', 'database_url': SecretStr(''), 'admin_database_url': SecretStr(''),
        'sqlite_path': '/tmp/opencode/agentic-pilot/eval.db', 'execution_mode': 'agentic_rag',
        'allow_stale_generation': False, 'source_lookup_only': False, 'generation_enabled': True,
        'session_challenge_mode': 'disabled', 'local_embedding_model_dir': ROOT / 'models/e5',
    })
    if not settings.groq_api_key.get_secret_value() and not args.dry_run:
        raise SystemExit('GROQ_API_KEY is required for the live pilot')
    if not args.live and not args.dry_run:
        raise SystemExit('Offline mode is covered by pytest; pass --live for the approved real-model pilot')

    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    ledger = None if args.dry_run else PilotAllocation(
        LEDGER, 'agentic-rag-final-20261022', max_tokens=args.global_token_cap,
        max_requests=args.global_request_cap, per_request=3000)
    store = Store(settings)
    store.restore(ROOT / args.backup)
    release = store.release(None, True)
    for path in sorted((ROOT / args.receipts).glob('*.json')):
        record_source_review(store, path)
    activate_source_gate(store, ROOT / args.policy_v1)
    activate_source_gate(store, ROOT / args.policy)
    gate = store.source_gate_status(release, date(2026, 10, 22))
    if not gate or not gate.get('usable') or gate.get('eligible_passages') != 43:
        raise SystemExit(f'Source gate is not the frozen 43-passage candidate: {gate}')
    provider = DryProvider(settings) if args.dry_run else GroqProvider(
        settings, store, usage_scope='operator', request_budget=ledger)
    runner = BoundedAgenticRAG(store, provider)
    decisions = []
    original_tool_step = provider.tool_step

    async def traced_tool_step(instruction, messages, tools, budget, **kwargs):
        reply = await original_tool_step(instruction, messages, tools, budget, **kwargs)
        decisions.append({'step': 'tool_step', 'tool_calls': [call['name'] for call in reply.get('tool_calls') or []],
                          'content_chars': len(reply.get('content') or '')})
        return reply

    provider.tool_step = traced_tool_step
    report = {
        'mode': 'live-pre-deployment', 'suite_id': manifest['suite_id'],
        'suite_sha256': manifest['scenarios_sha256'], 'release_id': release['id'],
        'policy_sha256': manifest['policy_sha256'], 'model': settings.generation_model,
        'as_of': '2026-10-22', 'request_cap': args.request_cap, 'token_cap': args.token_cap,
        'global_request_cap': args.global_request_cap, 'global_token_cap': args.global_token_cap,
        'cases': [], 'stopped': None,
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    for index, case in enumerate(selected):
        if ledger is not None and len(ledger.entries) >= args.request_cap:
            report['stopped'] = 'pre_deployment_request_cap'
            break
        history = case.get('history') or []
        used = len(ledger.entries) if ledger is not None else 0
        print(f'[pilot] {case["id"]} requests_used={used}', flush=True)
        started = time.monotonic()
        record = {'id': case['id'], 'kind': case['kind'], 'message': case['message'],
                  'history': history, 'execution': 'RUN'}
        try:
            result = await runner.run(
                ChatRequest(session_id='0' * 36, message=case['message'], history=history,
                            project='ring4', as_of=date(2026, 10, 22), mode='agentic_rag'),
                lambda _: None, release['id'])
        except (RateLimited, ProviderUnavailable, BudgetExceeded) as exc:
            record.update(execution='ERROR', reason=type(exc).__name__)
            report['cases'].append(record)
            report['stopped'] = 'provider_or_budget_error'
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            break
        record.update({
            'elapsed_ms': int((time.monotonic() - started) * 1000), 'status': result.status,
            'answer': result.content, 'citations': [citation.model_dump(mode='json') for citation in result.citations],
            'evidence_chunk_ids': result.evidence_chunk_ids, 'retrieved_chunk_ids': result.retrieved_chunk_ids,
            'llm_calls': result.llm_calls, 'tool_calls': result.tool_calls,
            'embedding_calls': result.embedding_calls, 'token_usage': result.token_usage,
            'support_level': result.support_level,
            'trace': [event.model_dump(mode='json') for event in result.trace],
            'decisions': decisions[-3:],
        })
        report['cases'].append(record)
        report['budget'] = ledger.summary() if ledger is not None else {'dry_run': True}
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        if index < len(selected) - 1 and args.cooldown_seconds and not args.dry_run:
            await asyncio.sleep(args.cooldown_seconds)
    report['budget'] = ledger.summary() if ledger is not None else {'dry_run': True}
    report['total_requests'] = report['budget'].get('requests_reserved', 0)
    report['total_confirmed_usage'] = report['budget'].get('confirmed_usage', 0)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    store.close()
    print(json.dumps({'cases': [case.get('id') for case in report['cases']],
                      'budget': report['budget'], 'stopped': report['stopped']}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
