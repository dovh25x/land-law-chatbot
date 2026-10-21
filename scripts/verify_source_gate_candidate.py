"""Offline source-gate replay on a separate SQLite database; never calls Groq.

Deterministic source facts run through the real Agent. A separate, explicitly
labelled synthesis fixture checks plumbing only and is not model evaluation.
"""
import argparse
import asyncio
import hashlib
import json
import tempfile
import time
from datetime import date
from pathlib import Path

from landlaw.agent import Agent, SupportingSpan, Verification
from landlaw.config import Settings
from landlaw.local_embedding import Encoder, MODEL
from landlaw.models import ChatRequest, Claim, Draft
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.evaluation import configuration_fingerprint
from landlaw.security import local_date, utcnow
from landlaw.store import Store


class OfflineProvider:
    # Explicit injection into a test Agent, never registered by the application.
    configured = True

    def __init__(self, settings, encoder, fixture=None):
        self.settings, self.encoder, self.fixture = settings, encoder, fixture
        self.fixture_calls = 0

    async def embed(self, text, title=None, query=False, budget=None, release=None):
        if budget:
            budget.embedding_calls += 1
        return await asyncio.to_thread(self.encoder.encode, text, query)

    async def generate(self, schema, instruction, payload, budget):
        if self.fixture is None:
            raise RuntimeError('External generation is disabled in the offline source replay')
        budget.llm()
        self.fixture_calls += 1
        if schema is Draft:
            return Draft(status='answered', claims=[self.fixture])
        if schema is Verification:
            spans = [SupportingSpan(claim_index=i, citation_id=cid, span_id=span['span_id'])
                for i, claim in enumerate(payload['draft']['claims']) for cid in claim['citation_ids']
                for span in payload['source_spans'] if span['citation_id'] == cid]
            return Verification(supported_claim_indexes=list(range(len(payload['draft']['claims']))),
                                supporting_spans=spans)
        raise RuntimeError('No planner fixture is provided')


async def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    inputs = [args.backup, args.policy, *sorted(args.receipts.glob('*.json')), Path(__file__)]
    input_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    # Refuse downloads. Only the pinned, already installed E5 files are allowed.
    for name, checksum in [('model_quantized.onnx', MODEL['onnx_sha256']),
                           ('sentencepiece.bpe.model', MODEL['tokenizer_sha256'])]:
        path = Path('models/e5')/name
        if not path.is_file() or Encoder.file_sha(path) != checksum:
            raise ValueError('Pinned local embedding files are required; downloads disabled')
    encoder = Encoder(Path('models/e5'))
    cases = {row['id']: row for split in ('smoke', 'supplemental', 'natural')
             for line in (Path('data/evaluation')/(split+'.jsonl')).read_text().splitlines()
             if (row := json.loads(line))}
    with tempfile.TemporaryDirectory(prefix='landlaw-source-gate-') as folder:
        settings = Settings(_env_file=None, app_env='development', database_url='', admin_database_url='',
            groq_api_key='', sqlite_path=str(Path(folder)/'candidate.db'), allow_stale_generation=False)
        store = Store(settings)
        runtime_fingerprint = configuration_fingerprint(settings)
        try:
            store.restore(args.backup)
            release = store.release(None, True)
            before = store.source_review_states(release)
            receipts = []
            for path in sorted(args.receipts.glob('*.json')):
                receipts.append(record_source_review(store, path))
            activated = activate_source_gate(store, args.policy)
            records = []
            async def execute(ident, question, as_of, *, history=None, fixture=None, kind='deterministic'):
                provider = OfflineProvider(settings, encoder, fixture)
                events = []
                async def emit(event): events.append(event.model_dump(mode='json'))
                captured = {}
                class RecordingAgent(Agent):
                    async def finish(self, state):
                        captured['contexts'] = self.context(state)
                        captured['draft'] = state['draft'].model_dump(mode='json')
                        captured['verifier'] = state['verification'].model_dump(mode='json')
                        captured['source_reviews'], captured['source_issues'] = await self.claim_source_reviews(state, state['draft'].claims)
                        return await super().finish(state)
                agent = RecordingAgent(store, provider)
                start = time.monotonic()
                result = await agent.run(ChatRequest(session_id='0'*36, message=question,
                    as_of=date.fromisoformat(as_of), history=history or []), emit)
                integrity = all((chunk := store.chunk(c.id, release['id'])) is not None
                    and c.excerpt == chunk.text and c.locator == chunk.locator
                    and c.document_id == chunk.document_id for c in result.citations)
                records.append({'id': ident, 'kind': kind, 'question': question, 'as_of': as_of,
                    'elapsed_ms': round((time.monotonic()-start)*1000), 'external_llm_requests': 0,
                    'fixture_generate_calls': provider.fixture_calls, 'answer': result.model_dump(mode='json'),
                    'citation_integrity': integrity, 'events': events, **captured})
                with (args.output/'attempts.jsonl').open('a') as output:
                    output.write(json.dumps(records[-1], ensure_ascii=False)+'\n')
            for ident in ('S01', 'S02', 'S03', 'N07', 'N08'):
                row = cases[ident]
                await execute(ident, row['question'], row['as_of'], history=row.get('history'))
            await execute('UNREVIEWED-CURRENT', 'Điều 104 Luật Đất đai 2024 quy định bồi thường di chuyển tài sản như thế nào?',
                          str(local_date()))
            # Fixture deliberately quotes a retained source, not a generated gold answer.
            chunk = store.chunk(cases['N01']['gold_chunk_ids'][0], release['id'])
            row = cases['N01']
            await execute('N01-SYNTHESIS-FIXTURE', row['question'], row['as_of'],
                fixture=Claim(text=chunk.text, citation_ids=[chunk.id]), kind='synthetic_synthesis_not_model_evaluation')
            backup = args.output/'corpus-with-source-gate.json'
            store.backup(backup)
            restored = Store(settings.model_copy(update={'sqlite_path': str(Path(folder)/'restore.db')}))
            try:
                restored.restore(backup)
                restore_closed = not restored.source_gate_status(restored.release(None, True))['usable']
                for path in sorted(args.receipts.glob('*.json')): record_source_review(restored, path)
                restore_open = restored.source_gate_status(restored.release(None, True))['usable']
                restore_exact = restored.release()['documents'] == store.release()['documents']
            finally: restored.close()
            assert input_hashes == {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
            assert configuration_fingerprint(settings) == runtime_fingerprint
            report = {'checked_at': utcnow().isoformat(), 'storage_backend': 'isolated_sqlite',
                'configuration_sha256': runtime_fingerprint, 'inputs_sha256': input_hashes,
                'inputs_unchanged_during_replay': True, 'corpus_id': release['id'],
                'source_gate': store.source_gate_status(release), 'activation': activated,
                'before': before, 'after': store.source_review_states(release), 'receipts': receipts,
                'external_llm_requests': 0, 'external_llm_tokens': 0,
                'restore': {'exact_documents': restore_exact, 'missing_receipts_fail_closed': restore_closed,
                            'receipts_reapplied_usable': restore_open,
                            'backup_sha256': hashlib.sha256(backup.read_bytes()).hexdigest()},
                'cases': records,
                'scope': 'Offline deterministic behavior and a labelled synthesis fixture only. Not a model benchmark or public/PG E2E.'}
            (args.output/'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
            print(json.dumps({'cases': [{'id':r['id'],'status':r['answer']['status'],
                'citations':len(r['answer']['citations']),'fixture_calls':r['fixture_generate_calls']} for r in records],
                'restore': report['restore'], 'gate': report['source_gate']}, ensure_ascii=False))
        finally: store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--receipts', type=Path, required=True)
    parser.add_argument('--policy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
