"""Scoped verbatim-quote plumbing and real FastAPI startup; never a model pass."""
import asyncio
import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from landlaw.agent import Agent, Plan, SupportingSpan, Verification
from landlaw.api import create_app
from landlaw.config import Settings
from landlaw.local_embedding import Encoder, MODEL
from landlaw.models import ChatRequest, Claim, Draft
from landlaw.ops import record_source_review
from landlaw.store import Store
from scripts.verify_source_gate_candidate import OfflineProvider

OUT = Path(__file__).parent


class QuoteFixture(OfflineProvider):
    async def generate(self, schema, instruction, payload, budget):
        budget.llm()
        if schema is Draft:
            shown = next(e for e in payload['evidence'] if e['document_id'] == 'luat-dat-dai-2024'
                         and e['locator'].split(' · ')[0] == 'Điều 108')
            return Draft(status='answered', claims=[Claim(text=shown['text'], citation_ids=[shown['citation_id']])])
        if schema is Verification:
            return Verification(supported_claim_indexes=[0], supporting_spans=[
                SupportingSpan(claim_index=0, citation_id=s['citation_id'], span_id=s['span_id'])
                for s in payload['source_spans']])
        if schema is Plan:
            raise AssertionError('Explicit article lookup must not require a model planner')
        raise AssertionError('Unexpected fixture schema')


async def quote_check(store, settings, encoder):
    snapshot = {}
    class Observed(Agent):
        async def finish(self, state):
            snapshot.update(synthesis_sources=state['synthesis_sources'],
                admitted_source_ids=sorted(state['admitted_source_ids']),
                verification=state['verification'].model_dump(mode='json'))
            return await super().finish(state)
    async def emit(event):
        pass
    result = await Observed(store, QuoteFixture(settings, encoder)).run(ChatRequest(session_id='0' * 36,
        message='Khoản 1 Điều 108 Luật Đất đai 2024 quy định những khoản hỗ trợ nào khi thu hồi đất '
                'cho Vành đai 4 Hà Nội ngày 21/10/2026? Chỉ trích nội dung nguồn, không xác nhận quyền lợi cá nhân.',
        as_of=date(2026, 10, 21)), emit)
    rows = [(c.document_id, c.id, store.chunk(c.id).checksum) for c in result.citations]
    reviews = store.scoped_source_reviews(store.release(None, True), rows, date(2026, 10, 21))
    return {'kind': 'verbatim_source_and_semantic_judge_fixture_not_model',
        'answer': result.model_dump(mode='json'), **snapshot,
        'all_released_citations_reviewed': bool(rows) and all(v == 'fresh' for v in reviews.values()),
        'all_released_citations_in_snapshot': all(c.id in snapshot['synthesis_sources'] for c in result.citations),
        'external_llm_requests': 0, 'model_pass': None}


def run():
    for name, expected in [('model_quantized.onnx', MODEL['onnx_sha256']),
                           ('sentencepiece.bpe.model', MODEL['tokenizer_sha256'])]:
        assert Encoder.file_sha(Path('models/e5') / name) == expected
    encoder = Encoder(Path('models/e5'))
    with tempfile.TemporaryDirectory(prefix='landlaw-phase3b-startup-') as folder:
        settings = Settings(_env_file=None, app_env='development', database_url='', admin_database_url='',
            groq_api_key='', allow_stale_generation=False, sqlite_path=str(Path(folder) / 'test.db'))
        store = Store(settings)
        try:
            store.restore(OUT / 'local-corpus-backup.json')
            for p in sorted(Path('reports/phase2c-current-20261021/receipts-final').glob('*.json')):
                record_source_review(store, p)
            gate = store.source_gate_status(store.release(None, True))
            assert gate['usable']
            quote = asyncio.run(quote_check(store, settings, encoder))
            with TestClient(create_app(settings, store=store)) as client:
                health = client.get('/healthz')
                ready = client.get('/readyz')
                status = client.get('/api/v1/status')
            report = {'storage_backend': 'isolated_sqlite', 'source_gate_usable': gate['usable'],
                'health_status': health.status_code, 'ready_status': ready.status_code,
                'ready': ready.json(), 'api_status': status.json(), 'quote_fixture': quote,
                'production_database_touched': False, 'external_llm_requests': 0,
                'scope': 'Real app lifespan and endpoints; empty API key intentionally gives readiness503. '
                    'Separately, a verbatim reviewed-source fixture proves release plumbing only; '
                    'semantic judge is a fixture and this does not certify a legal answer or live model.'}
            (OUT / 'startup-and-positive-fixture-final.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
            print(json.dumps({'health_status': health.status_code, 'ready_status': ready.status_code,
                'positive_fixture_status': quote['answer']['status'],
                'all_citations_reviewed': quote['all_released_citations_reviewed'],
                'all_citations_in_snapshot': quote['all_released_citations_in_snapshot']}))
        finally:
            store.close()


def forbidden(*args, **kwargs):
    raise AssertionError('Real HTTP forbidden')


async def async_forbidden(*args, **kwargs):
    raise AssertionError('Real HTTP forbidden')


with patch.object(httpx.HTTPTransport, 'handle_request', forbidden), \
        patch.object(httpx.AsyncHTTPTransport, 'handle_async_request', async_forbidden):
    run()
