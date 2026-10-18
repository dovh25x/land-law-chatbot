"""Evaluate frozen suites locally; resume checkpoints without touching serving DB."""
import argparse
import asyncio
import json
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint, evaluate
from landlaw.provider import GroqProvider, ProviderUnavailable
from landlaw.security import utcnow
from landlaw.store import Store
from psycopg import sql
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr


def lock_configuration(settings, output):
    fingerprint = configuration_fingerprint(settings)
    path = output/'configuration-lock.json'
    if path.exists():
        if json.loads(path.read_text())['configuration_sha256'] != fingerprint:
            raise ValueError('Source/configuration changed; use a new evaluation output')
    else:
        existing = [json.loads(p.read_text())['configuration_sha256']
                    for p in (output/'runs').glob('*/metadata.json')]
        if any(value != fingerprint for value in existing):
            raise ValueError('Historical output has a different configuration')
        path.write_text(json.dumps({'configuration_sha256': fingerprint}, indent=2)+'\n')
    return fingerprint


@contextmanager
def candidate_settings(args, folder):
    settings = Settings().for_operator().model_copy(update={'reports_dir': args.output})
    if not args.postgres:
        yield settings.model_copy(update={
            'database_url': SecretStr(''), 'admin_database_url': SecretStr(''),
            'sqlite_path': str(Path(folder)/'candidate.db')})
        return
    owner = settings.admin_database_url.get_secret_value()
    if not owner:
        raise ValueError('Isolated PostgreSQL evaluation requires an owner connection')
    name = 'landlaw_generation_'+uuid.uuid4().hex[:16]
    with psycopg.connect(owner, autocommit=True, connect_timeout=15) as control:
        control.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        try:
            isolated = make_conninfo(owner, dbname=name)
            with psycopg.connect(isolated, autocommit=True, connect_timeout=15) as connection:
                for migration in sorted(Path('migrations').glob('*.sql')):
                    connection.execute(migration.read_text())
            yield settings.model_copy(update={'database_url': SecretStr(isolated),
                                               'admin_database_url': SecretStr('')})
        finally:
            # This name was generated and created above by this invocation.
            # Never migrate, restore into, or remove the configured serving DB.
            control.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))


async def main(args):
    if args.output.exists() and not args.resume:
        raise ValueError('Output exists; use --resume for the same frozen run or select a new directory')
    args.output.mkdir(parents=True, exist_ok=True)
    cooldown_path = args.output/'operator-cooldown.json'
    if cooldown_path.exists():
        cooldown = json.loads(cooldown_path.read_text())
        if datetime.fromisoformat(cooldown['not_before']) > utcnow():
            print(json.dumps({'deferred_until': cooldown['not_before'], 'generation_calls': 0}))
            return
    with tempfile.TemporaryDirectory(prefix='landlaw-generation-candidate-') as folder, candidate_settings(args, folder) as settings:
        fingerprint = lock_configuration(settings, args.output)
        store = Store(settings)
        provider = GroqProvider(settings, store, usage_scope='operator')
        generate = provider.generate
        async def frozen_generate(*positional, **keyword):
            if configuration_fingerprint(settings) != fingerprint:
                raise ValueError('Source changed during model evaluation')
            return await generate(*positional, **keyword)
        provider.generate = frozen_generate
        try:
            store.restore(args.backup)
            for split in args.split or ('smoke', 'supplemental', 'natural'):
                if configuration_fingerprint(settings) != fingerprint:
                    raise ValueError('Source changed between frozen suites')
                report = await evaluate(settings, store, provider, split, concurrency=1)
                if configuration_fingerprint(settings) != fingerprint:
                    raise ValueError('Source changed during frozen suite')
                print(json.dumps({'split': split, 'run_id': report['run_id'], 'results': report['results']}), flush=True)
                remaining = store.cooldown()
                cooldown_path.write_text(json.dumps({
                    'not_before': (utcnow()+timedelta(seconds=remaining)).isoformat(),
                    'source': 'Provider Retry-After observed by the operator run; not an application quota',
                }, indent=2)+'\n')
                if remaining > 60:
                    break
        finally:
            await provider.close()
            store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--split', action='append', choices=('smoke', 'supplemental', 'natural'))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--postgres', action='store_true', help='Use a newly created disposable PostgreSQL database; never the serving database')
    args = parser.parse_args()
    try:
        asyncio.run(main(args))
    except (ValueError, OSError, RuntimeError, sqlite3.Error, psycopg.Error, ProviderUnavailable) as error:
        # Validation/driver errors may include environment values; do not echo them.
        print(json.dumps({'passed': False, 'error_type': type(error).__name__}))
        raise SystemExit(1) from None
