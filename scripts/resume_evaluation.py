"""Resume a fixed evaluation after provider cooldowns; never score or publish.

Run with the existing operator environment. Checkpoints and every failed attempt
remain intact. No model/provider changes or application daily quotas are added.
"""
import argparse
import datetime
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time


def full_turn_cooldown(provider_wait, quota, failures, observed_paired_tokens=0):
    """Estimate recovery for work already lost, from observed provider data."""
    delay = provider_wait
    if quota.get('scope') == 'TPD' and all(isinstance(quota.get(k), int)
            for k in ('limit', 'used', 'requested')):
        deficit = quota['requested'] - max(0, quota['limit'] - quota['used'])
        if deficit > 0:
            consumed = max((r['result'].get('token_usage', 0) for r in failures), default=0)
            # The paired mode may have already completed this same question.
            # Use its measured full-turn cost when the first request was
            # blocked, so a subsequent draft does not starve its verifier.
            remaining_work = max(consumed, observed_paired_tokens - quota['requested'])
            delay += math.ceil(remaining_work * provider_wait / deficit)
    return delay


def wait_for_recovery(seconds, credentials_changed):
    """A newly supplied credential needs a new capacity check, not old backoff."""
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if credentials_changed():
            print(json.dumps({'provider_credentials_changed': True,
                'action': 'recheck_capacity_with_same_generation_configuration'}), flush=True)
            return
        time.sleep(min(5, max(0, until - time.monotonic())))


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
    def credentials_changed():
        nonlocal settings
        current = Settings()
        if configuration_fingerprint(current) != configuration:
            raise SystemExit('Configuration changed; resume explicitly under the new fingerprint')
        if (current.llm_provider == 'groq' and current.groq_api_key.get_secret_value()
                and current.groq_api_key.get_secret_value() != settings.groq_api_key.get_secret_value()):
            settings = current
            return True
        return False
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
            wait_for_recovery(delay, credentials_changed)
        while True:
            # Changing .env or generation code requires a separate run, never
            # an invisible model switch inside this checkpoint.
            if configuration_fingerprint(Settings()) != configuration:
                raise SystemExit('Configuration changed; resume explicitly under the new fingerprint')
            quota = {}
            completed = subprocess.Popen([sys.executable, '-m', 'landlaw.cli', 'benchmark',
                '--release-id', args.release_id, '--split', args.split,
                '--limit', '240', '--concurrency', '1'], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in completed.stdout:
                print(line, end='', flush=True)
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and 'evaluation_provider_quota' in event:
                    quota = event['evaluation_provider_quota']
            returncode = completed.wait()
            if returncode:
                raise SystemExit(returncode)
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
            provider_wait = max(waits)
            # A completed draft is not reusable after a failed turn. Waiting
            # only for the failed verifier's deficit would spend all newly
            # refilled tokens on another draft, starving verification forever.
            # Infer refill timing from actual provider quota/Retry-After and
            # include tokens already consumed by this same failed turn.
            failed_cases = {r['case_id'] for r in failures}
            observed_paired_tokens = max((r['result'].get('token_usage', 0) for r in records
                if r['case_id'] in failed_cases and r['result']['status'] not in {'limited', 'error'}), default=0)
            delay = full_turn_cooldown(provider_wait, quota, failures, observed_paired_tokens)
            next_attempt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay)
            print(json.dumps({'provider_retry_after_seconds': provider_wait,
                'estimated_full_turn_wait_seconds': delay,
                'resume_at': next_attempt.isoformat(), 'run_id': report['run_id']}), flush=True)
            wait_for_recovery(delay, credentials_changed)


if __name__ == '__main__':
    main()
