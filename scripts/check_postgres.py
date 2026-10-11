"""Live PostgreSQL checks. Creates only disposable technical sessions/counters."""
import json
import uuid
from pathlib import Path

import psycopg
from landlaw.config import Settings
from landlaw.security import new_token, utcnow
from landlaw.store import RateLimited, Store


def main():
    settings = Settings()
    runtime, operator = Store(settings), Store(settings.for_operator())
    checks, ids = {}, []
    try:
        checks['connected'] = runtime.ready()
        privileges = runtime.rows("SELECT has_table_privilege(current_user,'public.documents','SELECT') AS read, has_table_privilege(current_user,'public.documents','INSERT') AS write")
        checks['runtime_read_only_corpus'] = privileges[0]['read'] and not privileges[0]['write']
        for _ in range(2):
            sid, token = str(uuid.uuid4()), new_token()
            runtime.create_session(sid, token)
            ids.append((sid, token))
        checks['session_isolation'] = runtime.authenticate(*ids[0]) and not runtime.authenticate(ids[0][0], ids[1][1])
        key = 'technical-integration:' + str(uuid.uuid4())
        runtime.consume([(key, 1, 60)])
        try:
            runtime.consume([(key, 1, 60)])
            checks['atomic_quota'] = False
        except RateLimited:
            checks['atomic_quota'] = runtime.rows('SELECT value FROM counters WHERE key=?', (key,))[0]['value'] == 1
        with psycopg.connect(settings.for_operator().database_url.get_secret_value(), prepare_threshold=None) as conn:
            try:
                with conn.transaction():
                    conn.execute('SET LOCAL ROLE anon')
                    conn.execute('SELECT count(*) FROM public.documents')
                checks['anonymous_corpus_denied'] = False
            except psycopg.errors.InsufficientPrivilege:
                checks['anonymous_corpus_denied'] = True
        checks['database_mb'] = float(operator.rows('SELECT pg_database_size(current_database())/1024.0/1024.0 AS mb')[0]['mb'])
        checks['database_within_reserve'] = checks['database_mb'] < 350
    finally:
        for sid, _ in ids:
            with operator.transaction() as conn:
                operator.execute(conn, 'DELETE FROM sessions WHERE id=?', (sid,))
        runtime.close(); operator.close()
    passed = all(value for key, value in checks.items() if key != 'database_mb')
    report = {'checked_at': utcnow().isoformat(), 'passed': passed, 'checks': checks}
    Path('reports/postgres-integration.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
