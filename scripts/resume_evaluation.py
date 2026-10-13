"""Resume a fixed evaluation after provider cooldowns; never score or publish.

Run with the existing operator environment. Checkpoints and every failed attempt
remain intact. No model/provider changes or application daily quotas are added.
"""
import argparse
import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-id', required=True)
    parser.add_argument('--split', choices=['smoke', 'dev', 'acceptance'], default='smoke')
    parser.add_argument('--not-before', help='Timezone-aware ISO timestamp from a provider cooldown')
    args = parser.parse_args()
    if not re.fullmatch(r'corpus-[0-9a-f]{16}', args.release_id):
        parser.error('Invalid release ID')
    from landlaw.config import Settings
    from landlaw.evaluation import configuration_fingerprint
    settings = Settings()
    configuration = configuration_fingerprint(settings)
    # One runner per fixed release/configuration, including independent shells.
    import fcntl
    lock_path = settings.reports_dir / f'.resume-{args.release_id}-{configuration}.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('A runner for this exact configuration is already active')
        if args.not_before:
            when = datetime.datetime.fromisoformat(args.not_before)
            if when.tzinfo is None:
                parser.error('--not-before requires a timezone')
            delay = max(0, when.timestamp() - time.time())
            print(json.dumps({'provider_cooldown_seconds': round(delay, 2)}), flush=True)
            time.sleep(delay)
        while True:
            # Changing .env or generation code requires a separate run, never
            # an invisible model switch inside this checkpoint.
            if configuration_fingerprint(Settings()) != configuration:
                raise SystemExit('Configuration changed; resume explicitly under the new fingerprint')
            completed = subprocess.run([sys.executable, '-m', 'landlaw.cli', 'benchmark',
                '--release-id', args.release_id, '--split', args.split,
                '--limit', '240', '--concurrency', '1'], check=False)
            if completed.returncode:
                raise SystemExit(completed.returncode)
            public_path = settings.reports_dir / ('smoke.json' if args.split == 'smoke' else 'latest.json')
            report = json.loads(public_path.read_text())
            if report.get('configuration_sha256') != configuration or report.get('release') != args.release_id:
                raise SystemExit('Checkpoint configuration/release mismatch')
            records = json.loads((settings.reports_dir / 'runs' / report['run_id'] / 'records.json').read_text())
            failures = [r for r in records if r['result']['status'] in {'limited', 'error'}]
            if not failures:
                print(json.dumps({'checkpoint_status': 'awaiting_source_review',
                    'completed_pairs': report['completed_pairs'], 'run_id': report['run_id']}), flush=True)
                return
            # A 90-second execution limit, schema/verification failure, or
            # missing dependency cannot be solved by blind retries.
            waits = [r['result'].get('retry_after') for r in failures]
            if any(not isinstance(wait, (int, float)) or wait <= 0 for wait in waits):
                raise SystemExit('Non-quota failure requires inspection; checkpoint preserved')
            delay = max(waits)
            next_attempt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay)
            print(json.dumps({'provider_retry_after_seconds': delay,
                'resume_at': next_attempt.isoformat(), 'run_id': report['run_id']}), flush=True)
            time.sleep(delay)


if __name__ == '__main__':
    main()
