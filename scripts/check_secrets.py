"""Scan source and public artifacts without requiring locally configured secrets."""
import re
import subprocess
from pathlib import Path

from dotenv import dotenv_values

PATTERNS = (
    re.compile(r'\bgsk_[A-Za-z0-9]{20,}\b'),
    re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
    re.compile(r'\bgithub_pat_[A-Za-z0-9_]{40,}\b'),
    re.compile(r'\bAKIA[A-Z0-9]{16}\b'),
    re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(r'postgres(?:ql)?://[^\s:/]+:[^\s@]{4,}@'),
)
SUFFIXES = {'.py', '.ts', '.tsx', '.js', '.mjs', '.html', '.json', '.jsonl', '.md', '.css', '.yml', '.yaml', '.toml'}


def find_leaks(paths, secrets=()):
    leaked = []
    for path in paths:
        if not path.is_file() or path.suffix not in SUFFIXES:
            continue
        content = path.read_text(errors='ignore')
        if any(secret in content for secret in secrets) or any(pattern.search(content) for pattern in PATTERNS):
            leaked.append(str(path))
    return sorted(set(leaked))


def main():
    values = dotenv_values('.env')
    secrets = [v for k, v in values.items() if v and k != 'VITE_TURNSTILE_SITE_KEY' and len(v) > 12
               and any(x in k for x in ('KEY', 'TOKEN', 'SECRET', 'DATABASE_URL'))]
    tracked = subprocess.check_output(['git', 'ls-files', '-co', '--exclude-standard', '-z']).decode().split('\0')
    paths = {Path(p) for p in tracked if p}
    paths.update(Path('frontend/dist').rglob('*'))
    leaked = find_leaks(paths, secrets)
    if leaked:
        raise SystemExit('Potential secret in files: ' + ', '.join(leaked))
    print('No configured secret or recognized credential pattern found in source and public artifacts.')


if __name__ == '__main__':
    main()
