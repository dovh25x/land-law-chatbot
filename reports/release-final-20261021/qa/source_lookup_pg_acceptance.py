"""GET-only fallback acceptance on the existing isolated Docker PostgreSQL DB.

No .env, migrations, restores, sessions or writes. Every application SQL
statement is intercepted and must be SELECT. The local runtime role is used.
"""
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


class ReadOnlyStore(Store):
    query_count = 0

    def execute(self, conn, sql, params=()):
        if not sql.lstrip().upper().startswith('SELECT '):
            raise AssertionError('Only read-only SELECTs are authorized for this acceptance')
        self.query_count += 1
        return super().execute(conn, sql, params)


class NeverGenerate:
    configured = False

    def __init__(self, settings):
        self.settings = settings
        self.calls = 0

    async def generate(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('No model request is authorized')


def main():
    output = HERE/'source-lookup-pg-acceptance.json'
    if output.exists():
        raise ValueError('Preserve the original acceptance receipt')
    # Fixed local trust connection; never read configured cloud/admin credentials.
    dsn = 'host=127.0.0.1 port=54558 dbname=landlaw_phase4_restore user=landlaw_phase4_runtime connect_timeout=5'
    settings = Settings(_env_file=None, app_env='development', database_url=dsn,
                        admin_database_url='', groq_api_key='', source_lookup_only=True,
                        generation_enabled=False, allow_stale_generation=False)
    expected_fp = '8ee1cd63c2ef531bc603848ce3d5b11334322e368d14c10fc73a81d339d51464'
    assert configuration_fingerprint(settings) == expected_fp
    store = ReadOnlyStore(settings)
    provider = NeverGenerate(settings)
    try:
        identity = store.rows('SELECT current_database() AS database, current_user AS role')[0]
        assert identity == {'database': 'landlaw_phase4_restore', 'role': 'landlaw_phase4_runtime'}
        corpus = store.release(None, True)
        assert corpus['id'] == 'corpus-1afca764aa6692e0'
        db_counts = {table: store.rows(f'SELECT count(*) AS n FROM {table}')[0]['n']
                     for table in ('documents', 'chunks', 'source_reviews')}
        assert db_counts['documents'] == 60 and db_counts['chunks'] == 7396
        privilege_checks = {table: store.rows("SELECT has_table_privilege(current_user,?, 'INSERT') AS allowed",
                            ('public.'+table,))[0]['allowed']
                            for table in ('messages', 'traces', 'answer_cache', 'releases', 'source_reviews')}
        assert not any(privilege_checks.values())
        role_flags = store.rows('SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user')[0]
        assert not role_flags['rolsuper'] and not role_flags['rolbypassrls']
        records = []
        with TestClient(create_app(settings, store, provider)) as client:
            for day, count in [('2026-10-21', 43), ('2026-10-22', 1), ('2024-08-02', 25)]:
                response = client.get('/api/v1/documents', params={'as_of': day})
                assert response.status_code == 200
                listed = response.json()
                assert listed['verified_passage_count'] == count and listed['references'] == []
                chunks = []
                for doc in listed['documents']:
                    detail = client.get('/api/v1/documents/'+doc['id'], params={'as_of': day})
                    assert detail.status_code == 200
                    body = detail.json()
                    assert body['relations'] == [] and body['whole_document_verified'] is False
                    actual = body['document']
                    assert actual['review_as_of'] == day and actual['applicability_verified'] is False
                    for chunk in actual['chunks']:
                        assert digest(chunk['text']) == chunk['checksum']
                        assert 'embedding' not in chunk
                        chunks.append({'document_id': doc['id'], 'id': chunk['id'],
                                       'locator': chunk['locator'], 'checksum': chunk['checksum']})
                assert len(chunks) == count
                records.append({'as_of': day, 'documents': len(listed['documents']),
                                'passages': len(chunks), 'chunks': chunks})
            status = client.get('/api/v1/status').json()
            ready = client.get('/readyz')
            assert status['source_lookup_only'] is True and status['generation_available'] is False
            assert status['capabilities']['citizen_answers'] is False
            assert ready.status_code == 200
            assert ready.json()['configuration_sha256'] == expected_fp
        assert provider.calls == 0
        after = {table: store.rows(f'SELECT count(*) AS n FROM {table}')[0]['n'] for table in db_counts}
        assert after == db_counts
        receipt = {'status': 'PASS', 'checked_at': datetime.now(UTC).isoformat(),
                   'storage_backend': 'isolated Docker PostgreSQL', 'database': identity['database'],
                   'runtime_role': identity['role'], 'role_flags': role_flags,
                   'insert_privileges': privilege_checks, 'database_counts_before_after_equal': after == db_counts,
                   'database_counts': db_counts, 'application_sql_select_only': True,
                   'application_select_queries': store.query_count, 'http_methods_executed': ['GET'],
                   'runtime_fingerprint': expected_fp, 'corpus_id': corpus['id'],
                   'records': records, 'external_llm_requests': 0, 'provider_generate_calls': provider.calls,
                   'cloud_database_touched': False, 'migrations_or_restore_performed': False,
                   'scope': 'Read-only current fallback API on pre-existing local PG16 candidate DB and least-privilege runtime role. Not cloud/public E2E, Turnstile, model inference, legal review renewal or a PG retrieval benchmark.'}
        output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({k:v for k,v in receipt.items() if k != 'records'}, ensure_ascii=False))
    finally:
        store.close()


if __name__ == '__main__':
    main()
