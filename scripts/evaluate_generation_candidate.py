"""Evaluate frozen suites locally; resume checkpoints without touching serving DB."""
import argparse
import asyncio
import json
import hashlib
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

import psycopg
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint, evaluate, frozen_dataset
from landlaw.provider import GroqProvider, ProviderUnavailable, BudgetExceeded
from landlaw.request_budget import RequestBudget
from landlaw.security import utcnow
from landlaw.ops import record_source_review, activate_source_gate
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


def lock_source_policy(store, backup, receipt_paths, policy_path, output):
    """Restore reviews explicitly; never silently reuse another source cohort."""
    receipts = [record_source_review(store, path) for path in receipt_paths]
    if policy_path is not None:
        activate_source_gate(store, policy_path)
    release = store.release(None, True)
    gate = store.source_gate_status(release)
    if gate is not None and not gate['usable']:
        raise ValueError('Scoped candidate requires recent imported source receipts before evaluation')
    identity = {'backup_sha256': hashlib.sha256(backup.read_bytes()).hexdigest(),
                'source_gate_sha256': gate['policy_sha256'] if gate else None,
                'receipt_files_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                         for path in sorted(receipt_paths)},
                'receipt_ids': sorted(row['receipt_sha256'] for row in receipts)}
    path = output/'source-policy-lock.json'
    if path.exists() and json.loads(path.read_text()) != identity:
        raise ValueError('Source review cohort changed; use a new evaluation output')
    if not path.exists():
        if list((output/'runs').glob('*/records.json')):
            raise ValueError('Historical run has no source policy binding; use a new output')
        path.write_text(json.dumps(identity, indent=2)+'\n')
    return identity


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
        with (args.output/'isolated-databases.jsonl').open('a') as receipt:
            receipt.write(json.dumps({'created_at':utcnow().isoformat(), 'database':name,
                                      'automatic_drop':False, 'serving_database_changed':False})+'\n')
        isolated = make_conninfo(owner, dbname=name)
        with psycopg.connect(isolated, autocommit=True, connect_timeout=15) as connection:
            for migration in sorted(Path('migrations').glob('*.sql')):
                connection.execute(migration.read_text())
        # Connections close normally; the isolated database is retained even on failure.
        yield settings.model_copy(update={'database_url': SecretStr(isolated),
                                           'admin_database_url': SecretStr('')})


async def main(args):
    if args.no_generation and not args.case_id:
        raise ValueError('Offline guard evaluation requires explicit frozen case IDs')
    if args.output.exists() and not args.resume:
        raise ValueError('Output exists; use --resume for the same frozen run or select a new directory')
    args.output.mkdir(parents=True, exist_ok=True)
    cooldown_path = args.output/'operator-cooldown.json'
    if cooldown_path.exists() and not args.no_generation:
        cooldown = json.loads(cooldown_path.read_text())
        if datetime.fromisoformat(cooldown['not_before']) > utcnow():
            print(json.dumps({'deferred_until': cooldown['not_before'], 'generation_calls': 0}))
            return
    with tempfile.TemporaryDirectory(prefix='landlaw-generation-candidate-') as folder, candidate_settings(args, folder) as settings:
        splits=args.split or ('smoke','supplemental','natural')
        cases={split:{case['id'] for case in frozen_dataset(settings.data_dir,split)[0]}
               for split in splits}
        if args.case_id and not set(args.case_id)<=set().union(*cases.values()):
            raise ValueError('Unknown frozen case ID for the selected suites')
        fingerprint = lock_configuration(settings, args.output)
        ledger_path=args.output/'request-budget.json'
        if (not args.no_generation and not ledger_path.exists()
                and list((args.output/'runs').glob('*/records.json'))):
            raise ValueError('Historical run has no request budget ledger; use a new output')
        request_budget=None if args.no_generation else RequestBudget(
            max_tokens=args.max_total_tokens,max_requests=args.max_requests,path=ledger_path,identity=fingerprint)
        if request_budget is not None and request_budget.blocked_reason:
            print(json.dumps({'test_budget_exhausted':request_budget.summary(),'generation_calls':0}))
            return
        store = Store(settings)
        provider = GroqProvider(settings, store, usage_scope='operator',request_budget=request_budget)
        generate = provider.generate
        async def frozen_generate(*positional, **keyword):
            if args.no_generation:
                raise ProviderUnavailable('Provider calls disabled for offline guard evaluation',retryable=False)
            if configuration_fingerprint(settings) != fingerprint:
                raise ValueError('Source changed during model evaluation')
            current_gate = store.source_gate_status(store.release(None, True))
            current_policy = current_gate['policy_sha256'] if current_gate else None
            if (current_policy != source_identity['source_gate_sha256']
                    or (current_gate is not None and not current_gate['usable'])
                    or any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != checksum
                           for path, checksum in source_identity['receipt_files_sha256'].items())):
                raise ValueError('Source policy changed during model evaluation')
            return await generate(*positional, **keyword)
        provider.generate = frozen_generate
        try:
            store.restore(args.backup)
            source_identity = lock_source_policy(store, args.backup, args.source_receipt,
                                                 args.source_gate, args.output)
            for split in splits:
                chosen=[identifier for identifier in args.case_id or [] if identifier in cases[split]]
                if args.case_id and not chosen:continue
                if configuration_fingerprint(settings) != fingerprint:
                    raise ValueError('Source changed between frozen suites')
                report = await evaluate(settings, store, provider, split, concurrency=1,case_ids=chosen or None)
                if configuration_fingerprint(settings) != fingerprint:
                    raise ValueError('Source changed during frozen suite')
                print(json.dumps({'split': split, 'run_id': report['run_id'], 'results': report['results']}), flush=True)
                metadata_path = settings.reports_dir/'runs'/report['run_id']/'metadata.json'
                metadata = json.loads(metadata_path.read_text())
                metadata['source_policy'] = source_identity
                metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n')
                if args.no_generation:
                    print(json.dumps({'generation_calls_disabled':True,'split':split,'case_ids':chosen}),flush=True)
                    continue  # Never clear an inherited provider cooldown.
                remaining = store.cooldown()
                cooldown_path.write_text(json.dumps({
                    'not_before': (utcnow()+timedelta(seconds=remaining)).isoformat(),
                    'source': 'Provider Retry-After observed by the operator run; not an application quota',
                }, indent=2)+'\n')
                if remaining > 60:
                    break
                if request_budget is not None and request_budget.blocked_reason:
                    break
        finally:
            await provider.close()
            store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--split', action='append', help='Legacy split or reviewed frozen suite from evaluation/registry.json')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--postgres', action='store_true', help='Use and retain a newly created isolated PostgreSQL database; never the serving database')
    parser.add_argument('--case-id', action='append', help='Prioritize an existing frozen case without changing its full-suite denominator')
    parser.add_argument('--no-generation', action='store_true', help='Enforce zero provider calls for explicitly selected deterministic cases')
    parser.add_argument('--max-total-tokens', type=int, default=60000,
                        help='Hard operator-test budget including conservative unknown usage, persisted across resume')
    parser.add_argument('--max-requests', type=int, default=18,
                        help='Total network attempts including retries, persisted across resume')
    parser.add_argument('--source-receipt', type=Path, action='append', default=[],
                        help='Import a checksum-bound source receipt into the isolated database')
    parser.add_argument('--source-gate', type=Path, help='Activate the reviewed candidate source policy locally')
    args = parser.parse_args()
    try:
        asyncio.run(main(args))
    except (ValueError, OSError, RuntimeError, sqlite3.Error, psycopg.Error, ProviderUnavailable, BudgetExceeded) as error:
        # Validation/driver errors may include environment values; do not echo them.
        print(json.dumps({'passed': False, 'error_type': type(error).__name__}))
        raise SystemExit(1) from None
