"""Run a real checkpoint on the free CI runner; never publish or score answers."""
import os
import re
import subprocess


def main():
    release = os.environ.get('EVALUATION_RELEASE', '')
    split = os.environ.get('EVALUATION_SPLIT', 'smoke')
    limit = os.environ.get('EVALUATION_LIMIT', '40')
    concurrency = os.environ.get('EVALUATION_CONCURRENCY', '1')
    case_ids = os.environ.get('EVALUATION_CASE_IDS', '')
    if not re.fullmatch(r'corpus-[0-9a-f]{16}', release) or split not in {'smoke', 'dev', 'acceptance'}:
        raise SystemExit('Invalid evaluation release or split')
    if not limit.isdigit() or not 1 <= int(limit) <= 240:
        raise SystemExit('Checkpoint size must be between 1 and 240 mode executions')
    if concurrency not in {'1','2'}:
        raise SystemExit('Evaluation concurrency must be one or two')
    if case_ids and not re.fullmatch(r'(?:S\d{2}|HL-\d{3})(?:,(?:S\d{2}|HL-\d{3})){0,119}',case_ids):
        raise SystemExit('Invalid priority case identifiers')
    args=['land-law', 'benchmark', '--release-id', release, '--split', split,
          '--limit', limit, '--concurrency', concurrency]
    if case_ids:args+=['--case-ids',case_ids]
    subprocess.run(args, check=True)


if __name__ == '__main__':
    main()
