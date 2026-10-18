"""Evaluate frozen suites locally; resume checkpoints without touching serving DB."""
import argparse
import asyncio
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from landlaw.config import Settings
from landlaw.evaluation import evaluate
from landlaw.provider import GroqProvider, ProviderUnavailable
from landlaw.security import utcnow
from landlaw.store import Store
from pydantic import SecretStr


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
    with tempfile.TemporaryDirectory(prefix='landlaw-generation-candidate-') as folder:
        settings = Settings().for_operator().model_copy(update={
            'database_url': SecretStr(''), 'admin_database_url': SecretStr(''),
            'sqlite_path': str(Path(folder)/'candidate.db'), 'reports_dir': args.output})
        store = Store(settings)
        provider = GroqProvider(settings, store, usage_scope='operator')
        try:
            store.restore(args.backup)
            for split in args.split or ('smoke', 'supplemental', 'natural'):
                report = await evaluate(settings, store, provider, split, concurrency=1)
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
    args = parser.parse_args()
    try:
        asyncio.run(main(args))
    except (ValueError, OSError, RuntimeError, sqlite3.Error, ProviderUnavailable) as error:
        # Validation/driver errors may include environment values; do not echo them.
        print(json.dumps({'passed': False, 'error_type': type(error).__name__}))
        raise SystemExit(1) from None
