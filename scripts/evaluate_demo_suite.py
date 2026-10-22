"""Run the 12-case demo evaluation against an isolated corpus copy.

Preflight never calls Groq: social and safety checks are deterministic, and legal
cases only exercise local E5 retrieval with a provider that refuses generation.
``--live`` is the only path that sends the five approved legal requests.
"""
import argparse
import asyncio
import hashlib
import json
import re
import subprocess
import tempfile
import uuid
from datetime import date
from pathlib import Path

from pydantic import SecretStr

from landlaw.agent import applicability
from landlaw.config import Settings
from landlaw.models import ChatRequest, Document
from landlaw.conversation import classify
from landlaw.ops import activate_source_gate
from landlaw.provider import GroqProvider, ProviderUnavailable
from landlaw.request_budget import BudgetExceeded
from landlaw.security import utcnow
from landlaw.simple_rag import SimpleAnswer, SimpleRAG
from landlaw.store import Store


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def sha256(value):
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def load_suite(path):
    manifest_path = path.with_name('manifest.json')
    manifest = json.loads(manifest_path.read_text())
    if sha256(path.read_bytes()) != manifest['scenarios_sha256']:
        raise SystemExit('Scenario hash does not match the frozen manifest')
    cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if len(cases) != manifest['cases']['total']:
        raise SystemExit('Scenario count does not match the manifest')
    return manifest, cases


def prepare_store(settings, backup, policy_path, policy_v1_path, receipts_dir):
    """Restore the corpus backup and import only the exactly pinned receipts."""
    policy = json.loads(policy_path.read_text())
    policy_v1 = json.loads(policy_v1_path.read_text())
    v1_hash = sha256(canonical(policy_v1))
    if policy.get('version') != 2 or policy.get('supersedes', {}).get('policy_sha256') != v1_hash:
        raise SystemExit('Policy v2 does not supersede the supplied v1 bytes')
    store = Store(settings)
    try:
        store.restore(backup)
        release = store.release(None, True)
        if not release:
            raise SystemExit('Backup has no active release')
        documents = {doc['id']: doc for doc in release.get('documents', [])}
        imported = set()
        for path in sorted(receipts_dir.glob('*.json')):
            receipt = json.loads(path.read_text())
            doc = documents.get(receipt.get('document_id'))
            encoded = canonical(receipt)
            ident = sha256(encoded)
            if not doc or doc.get('checksum') != receipt.get('checksum'):
                raise SystemExit(f'Receipt document mismatch: {path.name}')
            if policy.get('receipts', {}).get(doc['id']) != ident:
                raise SystemExit(f'Receipt is not pinned by the policy: {path.name}')
            with store.transaction() as conn:
                store.execute(conn, 'INSERT INTO source_reviews VALUES(?,?,?,?,?,?,?) '
                              'ON CONFLICT(id) DO NOTHING',
                              (ident, release['id'], doc['id'], doc['checksum'],
                               receipt['checked_at'], receipt['status'], encoded))
            imported.add(doc['id'])
        if imported != set(policy.get('receipts', {})):
            raise SystemExit('Receipt cohort does not exactly match the policy')
        activate_source_gate(store, policy_v1_path)
        activate_source_gate(store, policy_path)
        active = store.source_gate(release['id']) or {}
        if active.get('version') != 2 or sha256(canonical(active)) != sha256(canonical(policy)):
            raise SystemExit('Candidate policy did not activate byte-for-byte')
        status = store.source_gate_status(release, date.fromisoformat('2026-10-22'))
        if not status.get('usable') or status.get('eligible_passages') != 43:
            raise SystemExit('Candidate policy is not usable at the frozen as_of date')
        return store, release, policy
    except Exception:
        store.close()
        raise


class NoCallProvider:
    """Social replies must never reach embedding or generation."""

    configured = True

    def __init__(self, settings):
        self.settings = settings

    async def embed(self, *args, **kwargs):
        raise AssertionError('social intent attempted retrieval')

    async def generate(self, *args, **kwargs):
        raise AssertionError('social intent attempted generation')


class PreflightProvider(GroqProvider):
    """Loads local E5, then refuses the network generation step."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.refused_generations = 0

    async def generate(self, *args, **kwargs):
        self.refused_generations += 1
        raise ProviderUnavailable('PREFLIGHT_ONLY')


class CitationIntegrityProvider:
    configured = True

    def __init__(self, settings):
        self.settings = settings
        self.generations = 0

    async def embed(self, *args, **kwargs):
        return []

    async def generate(self, schema, instruction, payload, budget, **kwargs):
        self.generations += 1
        budget.llm()
        return SimpleAnswer(answer='Đủ điều kiện theo Điều 95 [S9].')


class DemoAllocation:
    """Fixed 3,000-token allocations for five approved legal requests."""

    def __init__(self, path, max_requests=5, max_tokens=15000, per_request=3000):
        self.path = Path(path)
        self.max_requests, self.max_tokens, self.per_request = max_requests, max_tokens, per_request
        self.entries = []
        self.actual_tokens = 0
        self.blocked_reason = None
        self.persist()

    def summary(self):
        reserved = sum(entry['reservation'] for entry in self.entries)
        return {
            'max_requests': self.max_requests,
            'reserved_token_cap': self.max_tokens,
            'reserved_tokens_per_request': self.per_request,
            'requests_reserved': len(self.entries),
            'reserved_tokens': reserved,
            'remaining_reserved_tokens': self.max_tokens - reserved,
            'reported_actual_tokens': self.actual_tokens,
            'blocked_reason': self.blocked_reason,
            'provider_quota_is_separate': True,
        }

    def persist(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        target = self.path.with_suffix(self.path.suffix + '.pending')
        target.write_text(json.dumps({'summary': self.summary(), 'entries': self.entries},
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
        self.entries.append({
            'id': ident, 'state': 'reserved', 'reservation': self.per_request,
            'wire_bytes': len(json.dumps(request, ensure_ascii=False, separators=(',', ':')).encode()),
            'confirmed_usage': None,
        })
        self.persist()
        return ident

    def settle(self, ident, usage, *, status_code=None, headers=None):
        entry = self.entries[ident]
        if entry['state'] != 'reserved':
            raise ValueError('Request allocation already settled')
        reported = usage.get('total_tokens') if isinstance(usage, dict) else None
        entry['http_status'] = status_code
        if type(reported) is int and reported >= 0:
            entry.update(state='confirmed', confirmed_usage=reported)
            self.actual_tokens += reported
            if self.actual_tokens >= self.max_tokens:
                self.blocked_reason = 'reported_actual_token_cap'
        else:
            entry['state'] = 'estimated'
        self.persist()


def marker_ids(text):
    return [f"S{match}" for match in re.findall(r"[\[【]\s*S(\d+)\s*[\]】]", text or '', re.I)]


NEGATED_CERTAINTY = re.compile(
    r"(?:chưa|không|ko|khó|chưa thể|không thể)\s+(?:đủ\s+)?(?:chắc chắn|chính xác)", re.I)


def forbidden_pattern_hit(pattern, text):
    """Match forbidden wording, but not a safe negated certainty phrase.

    L05 correctly says "chưa thể xác nhận ... đủ chắc chắn"; treating that as
    the forbidden assertion "chắc chắn" was a false positive. Numeric and
    outcome patterns are still matched against the raw text.
    """
    if pattern.strip().casefold() in {'chắc chắn', 'chính xác là'}:
        for match in re.finditer(pattern, text, re.I):
            prefix = text[max(0, match.start() - 60):match.start()].casefold()
            if re.search(r"\b(?:chưa|không|ko|khó)\b", prefix):
                continue
            return True
        return False
    return bool(re.search(pattern, text, re.I))


def auto_checks(case, result):
    checks = {}
    text = result.content or ''
    lower = text.casefold()
    if case.get('required_terms'):
        checks['required_terms'] = all(term.casefold() in lower for term in case['required_terms'])
    if case.get('required_patterns'):
        checks['required_patterns'] = all(re.search(pattern, text, re.I) for pattern in case['required_patterns'])
    if case.get('forbidden_patterns'):
        checks['forbidden_patterns'] = not any(forbidden_pattern_hit(pattern, text)
                                               for pattern in case['forbidden_patterns'])
    checks['status'] = result.status in case.get('expected_statuses', [])
    evidence = set(result.evidence_chunk_ids)
    checks['citations_from_evidence'] = all(citation.id in evidence for citation in result.citations)
    checks['min_citations'] = len(result.citations) >= case.get('min_citations', 0)
    checks['no_unknown_marker'] = not any(int(marker[1:]) > len(evidence) for marker in marker_ids(text))
    checks['one_request'] = result.llm_calls <= 1
    return checks


def case_record(case, result, execution):
    citations = [{
        'chunk_id': citation.id, 'document_id': citation.document_id,
        'locator': citation.locator, 'url': citation.url,
        'applicability': citation.applicability,
    } for citation in result.citations]
    record = {
        'id': case['id'], 'execution': execution, 'status': result.status,
        'answer': result.content, 'citations': citations,
        'evidence_chunk_ids': result.evidence_chunk_ids,
        'llm_calls': result.llm_calls, 'embedding_calls': result.embedding_calls,
        'token_usage': result.token_usage, 'elapsed_ms': result.elapsed_ms,
        'source_context': result.source_context,
        'trace': [{'step': event.step, 'summary': event.summary} for event in result.trace],
    }
    if execution == 'RUN':
        checks = auto_checks(case, result)
        record['auto_checks'] = checks
        record['auto_pass'] = all(checks.values())
        record['manual_review'] = None
    return record


async def run_social(case, settings, store):
    provider = NoCallProvider(settings)
    request = ChatRequest(session_id=uuid.uuid4().hex, message=case['message'],
                          as_of=date.fromisoformat('2026-10-22'), mode='simple_rag')
    result = await SimpleRAG(store, provider).run(request, None)
    intent = classify(case['message']).kind
    passed = (intent == case['expected_intent'] and result.status == case['expected_status']
              and result.llm_calls == 0 and result.embedding_calls == 0
              and not result.citations and not result.evidence_chunk_ids
              and all(term.casefold() in result.content.casefold()
                      for term in case.get('required_reply_terms', [])))
    return {
        'id': case['id'], 'kind': 'social', 'execution': 'RUN',
        'expected_intent': case['expected_intent'], 'actual_intent': intent,
        'status': result.status,
        'answer': result.content, 'llm_calls': result.llm_calls,
        'embedding_calls': result.embedding_calls, 'citations': 0,
        'evidence_chunk_ids': result.evidence_chunk_ids, 'passed': passed,
    }


async def run_legal_preflight(case, settings, store, provider):
    request = ChatRequest(session_id=uuid.uuid4().hex, message=case['message'],
                          as_of=date.fromisoformat('2026-10-22'), mode='simple_rag')
    result = await SimpleRAG(store, provider).run(request, None)
    retrieval_ok = bool(result.evidence_chunk_ids)
    return {
        'id': case['id'], 'kind': 'legal', 'execution': 'NOT RUN',
        'reason': 'GROQ_BUDGET_NOT_APPROVED',
        'preflight_retrieval': 'PASS' if retrieval_ok else 'FAIL',
        'evidence_chunk_ids': result.evidence_chunk_ids,
        'status': result.status, 'llm_calls': 0,
        'embedding_calls': result.embedding_calls,
        'refused_generations': provider.refused_generations,
        'answer': 'NOT RUN: real Groq generation was not approved.',
    }


async def run_legal_live(case, store, provider, allocation):
    if allocation.blocked_reason or len(allocation.entries) >= allocation.max_requests:
        return {
            'id': case['id'], 'kind': 'legal', 'execution': 'NOT RUN',
            'reason': allocation.blocked_reason or 'request_cap',
            'answer': 'NOT RUN: the approved provider budget was exhausted.',
        }
    if not provider.configured:
        raise SystemExit('GROQ_API_KEY is not configured; live evaluation was not started')
    request = ChatRequest(session_id=uuid.uuid4().hex, message=case['message'],
                          as_of=date.fromisoformat('2026-10-22'), mode='simple_rag')
    result = await SimpleRAG(store, provider).run(request, None)
    if result.status == 'limited' and allocation.blocked_reason in {
            'request_cap', 'reserved_token_cap', 'reported_actual_token_cap'}:
        return {
            'id': case['id'], 'kind': 'legal', 'execution': 'NOT RUN',
            'reason': allocation.blocked_reason,
            'answer': 'NOT RUN: the approved provider budget was exhausted.',
        }
    record = case_record(case, result, 'RUN')
    record['kind'] = 'legal'
    record['preflight_retrieval'] = 'PASS' if record['evidence_chunk_ids'] else 'FAIL'
    record['manual_review'] = {
        'task_success': None, 'grounded': None, 'false_abstention': None,
        'notes': '', 'reviewer': None, 'reviewed_at': None,
    }
    return record


async def run_live_legal_cases(cases, settings, store, allocation, cooldown):
    """Run all live legal cases in one event loop.

    Creating an httpx client outside the loop and closing each case with a new
    ``asyncio.run`` leaves the connection pool bound to a closed loop. The
    failed attempt is kept on disk by the allocation ledger; this function
    never retries a case and records an explicit ERROR if the harness itself
    fails after a request was reserved.
    """
    provider = GroqProvider(settings, store, usage_scope='operator',
                            request_budget=allocation)
    records = []
    try:
        if not provider.configured:
            raise SystemExit('GROQ_API_KEY is not configured; live evaluation was not started')
        for index, case in enumerate(cases):
            try:
                record = await run_legal_live(case, store, provider, allocation)
            except Exception as exc:  # preserve the attempt; never retry or repair
                record = {
                    'id': case['id'], 'kind': 'legal', 'execution': 'ERROR',
                    'reason': 'HARNESS_ERROR', 'error_type': type(exc).__name__,
                    'status': 'error', 'answer': 'ERROR: live runner failed before a result was persisted.',
                    'llm_calls': 0, 'embedding_calls': 0, 'token_usage': 0,
                    'citations': [], 'evidence_chunk_ids': [],
                    'manual_review': {
                        'task_success': None, 'grounded': None, 'false_abstention': None,
                        'notes': 'Runner error; this case is not a completed answer.',
                        'reviewer': None, 'reviewed_at': None,
                    },
                }
            records.append(record)
            if (record.get('execution') == 'RUN' and record.get('llm_calls', 0) > 0
                    and index < len(cases) - 1):
                await asyncio.sleep(cooldown)
    finally:
        await provider.close()
    return records


def safety_scope_and_dates(store, release, policy):
    as_of = date.fromisoformat('2026-10-22')
    status = store.source_gate_status(release, as_of)
    docs = {doc['id']: doc for doc in release['documents']}
    jurisdictions = sorted({docs[doc_id].get('jurisdiction') for doc_id in policy['standing']})
    allowed_jurisdictions = all(value in {'national', 'Hanoi', 'hanoi'} for value in jurisdictions)
    qd10 = policy['standing'].get('qd-10-2026-hanoi')
    qd10_states = store.scoped_source_reviews(
        release, [('qd-10-2026-hanoi', chunk_id, checksum)
                  for chunk_id, checksum in (qd10 or {}).get('chunks', {}).items()], as_of)
    expired_excluded = (applicability(Document.model_validate(docs['qd-10-2026-hanoi']), as_of) == 'historical'
                        and not any(value in {'fresh', 'standing', 'reviewed_window'}
                                    for value in qd10_states.values()))
    future = Document.model_validate({
        **docs['luat-dat-dai-2024'], 'id': 'future-synthetic', 'effective_from': date(2027, 1, 1),
        'effective_to': None, 'chunks': [],
    })
    future_excluded = applicability(future, as_of) == 'future'
    checks = {
        'reviewed_scope_only_national_or_hanoi': allowed_jurisdictions,
        'expired_qd10_excluded': expired_excluded,
        'synthetic_future_excluded': future_excluded,
        'current_count_43': status.get('eligible_passages') == 43,
        'review_mode_standing': status.get('mode') == 'standing_verified_snapshot',
    }
    return {'id': 'S01', 'kind': 'safety', 'execution': 'RUN', 'check': 'scope_and_dates',
            'jurisdictions': jurisdictions, 'checks': checks, 'passed': all(checks.values())}


def safety_citation_integrity(settings, store):
    provider = CitationIntegrityProvider(settings)
    request = ChatRequest(session_id=uuid.uuid4().hex,
                          message='Tôi có đủ điều kiện bồi thường về đất khi bị thu hồi không?',
                          as_of=date.fromisoformat('2026-10-22'), mode='simple_rag')
    result = asyncio.run(SimpleRAG(store, provider).run(request, None))
    evidence = set(result.evidence_chunk_ids)
    checks = {
        'fallback_used': result.status == 'clarification_needed',
        'unknown_marker_not_present': '[S9]' not in result.content.upper(),
        'citations_from_evidence': bool(result.citations)
        and all(citation.id in evidence for citation in result.citations),
        'one_simulated_generation': provider.generations == 1 and result.llm_calls == 1,
    }
    return {'id': 'S03', 'kind': 'safety', 'execution': 'RUN', 'check': 'citation_integrity',
            'simulated_generations': provider.generations, 'real_provider_requests': 0,
            'checks': checks, 'passed': all(checks.values())}


def safety_adverse_review(store, release, policy):
    doc_id = 'luat-thu-do-2026'
    doc = next(doc for doc in release['documents'] if doc['id'] == doc_id)
    before = store.source_gate_status(release, date(2026, 10, 22))['eligible_passages']
    stamp = utcnow().isoformat()
    receipt = json.dumps({'status': 'changed', 'checked_at': stamp, 'document_id': doc_id,
                          'checksum': doc['checksum']}, ensure_ascii=False, sort_keys=True)
    with store.transaction() as conn:
        store.execute(conn, 'INSERT INTO source_reviews VALUES(?,?,?,?,?,?,?)',
                      (str(uuid.uuid4()), release['id'], doc_id, doc['checksum'],
                       stamp, 'changed', receipt))
    after = store.source_gate_status(release, date(2026, 10, 22))['eligible_passages']
    removed = len(policy['standing'][doc_id]['chunks'])
    checks = {'adverse_count_drops': after == before - removed,
              'adverse_passages_not_admitted': after < before}
    return {'id': 'S02', 'kind': 'safety', 'execution': 'RUN', 'check': 'adverse_review',
            'before': before, 'after': after, 'removed': removed,
            'checks': checks, 'passed': all(checks.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path,
                        default=Path('data/evaluation/demo-v1-20261022/scenarios.jsonl'))
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--policy-v1', type=Path, required=True)
    parser.add_argument('--receipts', type=Path, required=True)
    parser.add_argument('--output', type=Path,
                        default=Path('reports/evaluation/demo-v1-20261022/preflight.json'))
    parser.add_argument('--live', action='store_true',
                        help='Send the five approved legal requests to Groq; all other checks stay deterministic')
    parser.add_argument('--cooldown-seconds', type=float, default=20,
                        help='Pause between live legal requests to respect the provider token window')
    args = parser.parse_args()
    if args.cooldown_seconds < 0:
        raise SystemExit('cooldown-seconds must not be negative')

    manifest, cases = load_suite(args.suite)
    if [case['id'] for case in cases] != [f'C{i:02d}' for i in range(1, 5)] + \
            [f'L{i:02d}' for i in range(1, 6)] + [f'S{i:02d}' for i in range(1, 4)]:
        raise SystemExit('Unexpected scenario IDs/order')
    if args.live and not args.output.name.endswith('live.json'):
        raise SystemExit('Use a distinct *live.json output so a preflight cannot be overwritten')
    output = {
        'suite_id': manifest['suite_id'], 'suite_sha256': manifest['scenarios_sha256'],
        'mode': 'live' if args.live else 'preflight',
        'generated_at': utcnow().isoformat(),
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'backup_sha256': sha256(args.backup.read_bytes()),
        'policy_sha256': sha256(canonical(json.loads(args.policy.read_text()))),
        'real_provider_requests': 0,
        'cases': [],
    }
    settings = Settings()
    with tempfile.TemporaryDirectory(prefix='landlaw-demo-eval-') as folder:
        isolated = settings.model_copy(update={
            'sqlite_path': str(Path(folder) / 'eval.db'),
            'database_url': SecretStr(''), 'admin_database_url': SecretStr(''),
        })
        store, release, policy = prepare_store(
            isolated, args.backup, args.policy, args.policy_v1, args.receipts)
        provider = None
        allocation = None
        live_records = {}
        try:
            if args.live:
                ledger = args.output.with_name(args.output.stem + '-budget-ledger.json')
                if ledger.exists():
                    raise SystemExit('Refusing to overwrite an existing live budget ledger')
                allocation = DemoAllocation(ledger)
                legal_cases = [case for case in cases if case['kind'] == 'legal']
                records = asyncio.run(run_live_legal_cases(
                    legal_cases, isolated, store, allocation, args.cooldown_seconds))
                live_records = {record['id']: record for record in records}
            else:
                provider = PreflightProvider(
                    isolated.model_copy(update={'groq_api_key': SecretStr('preflight-not-used')}),
                    store, usage_scope='operator')
            for case in cases:
                if case['kind'] == 'social':
                    output['cases'].append(asyncio.run(run_social(case, isolated, store)))
                elif case['kind'] == 'legal':
                    if args.live:
                        output['cases'].append(live_records[case['id']])
                    else:
                        output['cases'].append(
                            asyncio.run(run_legal_preflight(case, isolated, store, provider)))
                else:
                    if case['check'] == 'scope_and_dates':
                        output['cases'].append(safety_scope_and_dates(store, release, policy))
                    elif case['check'] == 'citation_integrity':
                        output['cases'].append(safety_citation_integrity(isolated, store))
                    elif case['check'] == 'adverse_review':
                        output['cases'].append(safety_adverse_review(store, release, policy))
                    else:
                        raise SystemExit(f'Unknown safety check: {case["check"]}')
            if allocation is not None:
                output['real_provider_requests'] = len(allocation.entries)
                output['budget'] = allocation.summary()
        finally:
            if provider is not None:
                asyncio.run(provider.close())
            store.close()

    social = [case for case in output['cases'] if case['kind'] == 'social']
    legal = [case for case in output['cases'] if case['kind'] == 'legal']
    safety = [case for case in output['cases'] if case['kind'] == 'safety']
    output['metrics'] = {
        'social_passed': sum(1 for case in social if case.get('passed')),
        'social_total': len(social),
        'legal_executed': sum(1 for case in legal if case.get('execution') == 'RUN'),
        'legal_not_run': sum(1 for case in legal if case.get('execution') == 'NOT RUN'),
        'legal_retrieval_passed': sum(1 for case in legal if case.get('preflight_retrieval') == 'PASS'),
        'legal_auto_passed': sum(1 for case in legal if case.get('auto_pass')),
        'safety_passed': sum(1 for case in safety if case.get('passed')),
        'safety_total': len(safety),
        'actual_tokens': sum(case.get('token_usage', 0) for case in legal),
        'llm_calls': sum(case.get('llm_calls', 0) for case in legal),
    }
    social_ok = output['metrics']['social_passed'] == len(social)
    safety_ok = output['metrics']['safety_passed'] == len(safety)
    if output['mode'] == 'preflight':
        complete = social_ok and safety_ok and output['metrics']['legal_retrieval_passed'] == len(legal)
        execution_ok = complete
    else:
        execution_ok = social_ok and safety_ok and all(
            case.get('llm_calls', 0) <= 1 for case in legal if case.get('execution') == 'RUN')
        complete = execution_ok and output['metrics']['legal_executed'] == len(legal)
    output['execution_passed'] = execution_ok
    output['complete'] = complete
    output['passed'] = complete
    output['quality_review'] = 'PENDING_MANUAL_REVIEW' if output['mode'] == 'live' else 'NOT_APPLICABLE'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'mode': output['mode'], 'passed': output['passed'],
                      'metrics': output['metrics'], 'output': str(args.output)},
                     ensure_ascii=False))
    if not output['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
