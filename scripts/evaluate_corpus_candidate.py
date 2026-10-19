"""Restore/evaluate an immutable candidate in isolated databases; never serving DB."""
import argparse
import asyncio
import json
import tempfile
import uuid
from pathlib import Path

import psycopg
from landlaw.config import Settings
from landlaw.evaluation import evaluate_retrieval
from landlaw.ingest import coverage
from landlaw.provider import GroqProvider
from landlaw.publication import validate_corpus
from landlaw.security import digest, utcnow
from landlaw.store import Store
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr


async def evaluate_store(settings, backup, expected, output):
    store = Store(settings.model_copy(update={'reports_dir': output}))
    provider = GroqProvider(settings, store)
    try:
        store.restore(backup)
        restored = store.release()
        assert restored['id'] == expected['id']
        assert restored['documents'] == expected['documents']
        assert restored['relations'] == expected['relations']
        for table in ('sessions', 'counters'):
            assert not store.rows(f'SELECT * FROM {table}')
        results = []
        for split in ('smoke', 'supplemental', 'natural'):
            report = await evaluate_retrieval(settings.model_copy(update={'reports_dir': output}), store, provider, split)
            results.append({key: report[key] for key in ('split', 'backend', 'gold_recall_at_8', 'hits', 'eligible_cases')})
            print(json.dumps(results[-1]), flush=True)
        summary = {'checked_at': utcnow().isoformat(), 'restored_exactly': True,
            'corpus_id': restored['id'], 'snapshot_sha256': digest(json.dumps(expected, sort_keys=True).encode()),
            'backup_sha256': digest(backup.read_bytes()), 'generation_calls': 0,
            'coverage': coverage(restored), 'retrieval': results}
        output.mkdir(parents=True, exist_ok=True)
        (output/'restore-and-retrieval.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    finally:
        await provider.close()
        store.close()


async def main(args):
    args.output.mkdir(parents=True, exist_ok=False)
    expected = json.loads(args.snapshot.read_text())
    validate_corpus(expected)
    settings = Settings()
    with tempfile.TemporaryDirectory(prefix='landlaw-candidate-eval-') as folder:
        local = settings.model_copy(update={'database_url': SecretStr(''), 'admin_database_url': SecretStr(''),
            'sqlite_path': str(Path(folder)/'candidate.db')})
        await evaluate_store(local, args.backup, expected, args.output/'sqlite')
    if args.postgres:
        owner = settings.admin_database_url.get_secret_value()
        if not owner:
            raise ValueError('Owner connection required for isolated restore')
        name = 'landlaw_restore_'+uuid.uuid4().hex[:12]
        with psycopg.connect(owner, autocommit=True, connect_timeout=15) as control:
            assert control.execute('SELECT current_database()').fetchone()[0] != name
            control.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
            with (args.output/'isolated-databases.jsonl').open('a') as receipt:
                receipt.write(json.dumps({'created_at':utcnow().isoformat(), 'database':name,
                                          'automatic_drop':False, 'serving_database_changed':False})+'\n')
            isolated = make_conninfo(owner, dbname=name)
            with psycopg.connect(isolated, autocommit=True, connect_timeout=15) as connection:
                for migration in sorted(Path('migrations').glob('*.sql')):
                    connection.execute(migration.read_text())
            selected = settings.model_copy(update={'database_url': SecretStr(isolated), 'admin_database_url': SecretStr('')})
            await evaluate_store(selected, args.backup, expected, args.output/'postgresql')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--postgres', action='store_true')
    args = parser.parse_args()
    try:
        asyncio.run(main(args))
    except (ValueError, AssertionError, OSError, psycopg.Error) as error:
        # Database driver exceptions may contain credentials; preserve type only.
        print(json.dumps({'passed': False, 'error_type': type(error).__name__}), flush=True)
        raise SystemExit(1) from None
