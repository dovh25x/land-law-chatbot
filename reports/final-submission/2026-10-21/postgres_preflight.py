"""Offline acceptance against a NEW loopback Docker database; never read .env.

No API calls, corpus edits, DROP or production connections. The container and
both databases are retained for review. Requires the separately authorized
landlaw-phase4-pg-20261021 container and its loopback published port.
"""
import argparse
import hashlib
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.security import new_token
from landlaw.store import Store
from psycopg import sql
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PRIOR = ROOT / 'reports/phase3b-reliability-20261021T073924Z'
LEGAL = ROOT / 'reports/phase2c-current-20261021'


def main(port):
    if not 1024 <= port <= 65535:
        raise ValueError('Expected a Docker loopback high port')
    output = OUT / 'postgres-preflight.json'
    if output.exists():
        raise ValueError('Preserve previous preflight evidence')
    started = datetime.now(UTC).isoformat()
    # These are local trust-auth DSNs, not credentials or .env values.
    def dsn(name, user='postgres'):
        assert name in {'landlaw_phase4', 'landlaw_phase4_restore'}
        assert user in {'postgres', 'landlaw_phase4_runtime'}
        return f'host=127.0.0.1 port={port} dbname={name} user={user} connect_timeout=5'

    with psycopg.connect(dsn('landlaw_phase4'), autocommit=True) as control:
        assert control.execute('SELECT current_database()').fetchone()[0] == 'landlaw_phase4'
        assert not control.execute("SELECT 1 FROM pg_tables WHERE schemaname='public'").fetchone()
        for name in ('anon', 'authenticated', 'landlaw_phase4_runtime'):
            control.execute(sql.SQL('CREATE ROLE {} {}').format(
                sql.Identifier(name), sql.SQL('LOGIN' if name.endswith('runtime') else 'NOLOGIN')))
        control.execute('CREATE DATABASE landlaw_phase4_restore')

    settings = Settings(_env_file=None, database_url=dsn('landlaw_phase4'),
        admin_database_url='', groq_api_key='', allow_stale_generation=False)
    migration_hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted((ROOT / 'migrations').glob('*.sql'))}
    for name in ('landlaw_phase4', 'landlaw_phase4_restore'):
        with psycopg.connect(dsn(name), autocommit=True) as conn:
            assert conn.execute('SELECT current_database()').fetchone()[0] == name
            for rel in migration_hashes:
                conn.execute((ROOT / rel).read_text())
            conn.execute('GRANT landlaw_runtime TO landlaw_phase4_runtime')

    stores = []
    try:
        admin = Store(settings)
        stores.append(admin)
        admin.restore(PRIOR / 'local-corpus-backup.json')
        release = admin.release(None, True)
        assert release['id'] == 'corpus-1afca764aa6692e0'
        receipts = sorted((LEGAL / 'receipts-final').glob('*.json'))
        for receipt in receipts:
            record_source_review(admin, receipt)
        activate_source_gate(admin, LEGAL / 'source-gate-final.json')
        assert admin.source_gate_status(release)['usable']
        runtime = Store(settings.model_copy(update={'database_url': SecretStr(dsn('landlaw_phase4', 'landlaw_phase4_runtime'))}))
        stores.append(runtime)
        sid = str(uuid.uuid4())
        token = new_token()
        runtime.create_session(sid, token)
        assert runtime.authenticate(sid, token) and not runtime.authenticate(sid, 'wrong')
        with ThreadPoolExecutor(max_workers=2) as pool:
            leases = list(pool.map(lambda _: runtime.start_turn(str(uuid.uuid4()), sid, 'fixture'), range(2)))
        assert leases.count(None) == 1 and leases.count('session_busy') == 1
        privileges = {}
        for table in ('messages', 'traces', 'answer_cache', 'releases', 'source_reviews'):
            allowed = runtime.rows("SELECT has_table_privilege(current_user,?, 'INSERT') AS allowed", ('public.'+table,))[0]['allowed']
            privileges[table] = allowed
            assert allowed is False
        for table in ('messages', 'traces', 'answer_cache'):
            assert admin.rows(f'SELECT count(*) AS n FROM {table}')[0]['n'] == 0
        runtime.set_cooldown(1)
        backup = OUT / 'local-postgres-corpus-backup.json'
        admin.backup(backup)
        restored = Store(settings.model_copy(update={'database_url': SecretStr(dsn('landlaw_phase4_restore'))}))
        stores.append(restored)
        restored.restore(backup)
        assert not restored.source_gate_status(restored.release(None, True))['usable']
        for receipt in receipts:
            record_source_review(restored, receipt)
        activate_source_gate(restored, LEGAL / 'source-gate-final.json')
        assert restored.source_gate_status(restored.release(None, True))['usable']
        assert admin.release()['documents'] == restored.release()['documents']
        documents = admin.rows('SELECT count(*) AS n FROM documents')[0]['n']
        chunks = admin.rows('SELECT count(*) AS n FROM chunks')[0]['n']
        assert (documents, chunks) == (60, 7396)
        version = admin.rows('SELECT version() AS version')[0]['version']
        extensions = admin.rows("SELECT extname,extversion FROM pg_extension WHERE extname IN ('vector','unaccent') ORDER BY extname")
        # No embeddings or model generation are needed for the round-trip check.
        result = {'status': 'PASS', 'started_at': started,
            'completed_at': datetime.now(UTC).isoformat(),
            'storage_backend': 'isolated_docker_postgresql', 'container': 'landlaw-phase4-pg-20261021',
            'loopback_only': True, 'databases_retained': ['landlaw_phase4','landlaw_phase4_restore'],
            'version': version, 'extensions': extensions, 'runtime_fingerprint': configuration_fingerprint(settings),
            'corpus_id': release['id'], 'documents': documents, 'chunks': chunks,
            'migrations_sha256': migration_hashes, 'runtime_role_tested': True,
            'session_authentication': True, 'concurrent_session_lease': True,
            'runtime_insert_privileges': privileges, 'server_conversation_rows': 0,
            'backup_document_roundtrip_exact': True, 'restore_without_receipts_fail_closed': True,
            'restore_receipts_reapplied_usable': True, 'source_gate_usable': True,
            'backup_file': str(backup.relative_to(ROOT)), 'backup_sha256': hashlib.sha256(backup.read_bytes()).hexdigest(),
            'external_llm_requests': 0, 'production_database_touched': False,
            'scope': 'Fresh local PG16/pgvector, migrations 001-006, restored candidate and receipts. Not Supabase/cloud, not model inference, not a 19-case retrieval benchmark or full pytest run.'}
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({k: result[k] for k in ('status','documents','chunks','runtime_fingerprint','external_llm_requests')}))
    finally:
        for store in reversed(stores):
            store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, required=True)
    args = parser.parse_args()
    main(args.port)
