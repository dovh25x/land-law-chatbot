"""Run a real checkpoint on the free CI runner; never publish or score answers."""
import os
import re
import subprocess


def main():
    release = os.environ.get('EVALUATION_RELEASE', '')
    split = os.environ.get('EVALUATION_SPLIT', 'smoke')
    limit = os.environ.get('EVALUATION_LIMIT', '40')
    if not re.fullmatch(r'corpus-[0-9a-f]{16}', release) or split not in {'smoke', 'dev', 'acceptance'}:
        raise SystemExit('Invalid evaluation release or split')
    if not limit.isdigit() or not 1 <= int(limit) <= 240:
        raise SystemExit('Checkpoint size must be between 1 and 240 mode executions')
    subprocess.run(['land-law', 'benchmark', '--release-id', release, '--split', split,
                    '--limit', limit, '--concurrency', '1'], check=True)


if __name__ == '__main__':
    main()
