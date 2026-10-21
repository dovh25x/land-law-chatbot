"""Exercise source-only API against the isolated QA copy of reviewed corpus."""
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from landlaw.api import create_app
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.security import digest
from landlaw.store import Store

HERE = Path(__file__).resolve().parent


class NeverGenerate:
    configured = False

    def __init__(self, settings):
        self.settings = settings
        self.calls = 0

    async def generate(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('Acceptance must never call a model')


def main():
    db = HERE/'source-scope-private.db'
    if not db.exists():
        raise ValueError('Requires the prior isolated corpus/receipt replay; never use configured DB')
    settings = Settings(_env_file=None, database_url='', admin_database_url='', groq_api_key='',
                        sqlite_path=str(db), source_lookup_only=True, generation_enabled=False,
                        allow_stale_generation=False)
    store = Store(settings)
    provider = NeverGenerate(settings)
    try:
        records = []
        with TestClient(create_app(settings, store, provider)) as client:
            for day in ('2024-08-02', '2026-10-21', '2026-10-22', '2026-10-23'):
                listed = client.get('/api/v1/documents', params={'as_of': day}).json()
                chunks = []
                for doc in listed['documents']:
                    response = client.get('/api/v1/documents/'+doc['id'], params={'as_of': day})
                    assert response.status_code == 200
                    detail = response.json()['document']
                    assert detail['whole_document_verified'] is False
                    assert detail['review_as_of'] == day
                    assert all(digest(c['text']) == c['checksum'] for c in detail['chunks'])
                    chunks.extend({'document_id': doc['id'], 'id': c['id'], 'locator': c['locator'],
                                   'checksum': c['checksum']} for c in detail['chunks'])
                assert len(chunks) == listed['verified_passage_count']
                assert listed['references'] == []
                records.append({'as_of': day, 'documents': len(listed['documents']), 'passages': len(chunks),
                                'chunks': chunks, 'catalog_references': 0})
            assert [row['passages'] for row in records] == [25, 43, 1, 1]
            status = client.get('/api/v1/status').json()
            ready_status = client.get('/readyz').status_code
            assert status['source_lookup_only'] is True and status['generation_available'] is False
            assert ready_status == 200 and provider.calls == 0
        output = {'status': 'PASS', 'checked_at': datetime.now(UTC).isoformat(),
                  'runtime_fingerprint': configuration_fingerprint(settings), 'storage_backend': 'isolated SQLite',
                  'corpus_id': store.release(None, True)['id'], 'mode': 'verified_source_lookup_only',
                  'records': records, 'ready_without_llm_key': ready_status == 200,
                  'external_llm_requests': 0, 'provider_generate_calls': provider.calls,
                  'production_database_touched': False,
                  'scope': 'Real source-only API with exact receipt/date/checksum filtering. Not generated legal answers, PG benchmark, cloud, Turnstile or public E2E.'}
        (HERE/'source-lookup-acceptance.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({key: value for key, value in output.items() if key != 'records'}, ensure_ascii=False))
    finally:
        store.close()


if __name__ == '__main__':
    main()
