"""Prepare a verified corpus-only GitHub Release asset; never publishes remotely."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from dotenv import dotenv_values
from landlaw.store import Store
from landlaw.publication import validate_corpus
from landlaw.security import utcnow
from check_secrets import PATTERNS


def prepare(source, output):
    payload = json.loads(source.read_bytes())
    if payload.get('format') != 1 or set(payload) != {'format', 'releases', 'state'}:
        raise ValueError('Only corpus/config backup schema is allowed; no sessions/messages/traces')
    active = next((r['value'] for r in payload['state'] if r['key'] == 'active_release'), None)
    if not active:
        raise ValueError('Backup requires an active release')
    if any(r['key'] not in {'active_release', 'previous_release'} and not r['key'].startswith('publication:')
           for r in payload['state']):
        raise ValueError('Unexpected application state in public backup')
    values = dotenv_values('.env')
    secrets = [v for k, v in values.items() if v and k != 'VITE_TURNSTILE_SITE_KEY' and len(v) > 12
               and any(x in k for x in ('KEY', 'TOKEN', 'SECRET', 'DATABASE_URL'))]
    decoded = []
    for row in payload['releases']:
        release = Store.decode_release(row['payload'])
        if release['id'] != row['id']:
            raise ValueError('Release ID mismatch')
        validate_corpus(release)
        for doc in release['documents']:
            for chunk in doc['chunks']:
                if hashlib.sha256(chunk['text'].encode()).hexdigest() != chunk['checksum']:
                    raise ValueError('Chunk checksum mismatch')
        decoded.append(release)
    texts = [source.read_text(), *(json.dumps(r, ensure_ascii=False) for r in decoded)]
    if any(secret in text for secret in secrets for text in texts) or any(
            pattern.search(text) for pattern in PATTERNS for text in texts):
        raise ValueError('Potential credential in public corpus; refusing packaging')
    current = next((r for r in decoded if r['id'] == active), None)
    if not current:
        raise ValueError('Active release is missing from backup')
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip())
    candidates = subprocess.check_output(['git', 'ls-files', '-co', '--exclude-standard', '-z']).decode().split('\0')
    hashes = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sorted(set(candidates))
              if name and not name.startswith('reports/') and Path(name).is_file()}
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'corpus-backup.json'
    shutil.copyfile(source, target)
    manifest = {'format': 1, 'prepared_at': utcnow().isoformat(), 'corpus_id': active,
                'documents': len(current['documents']),
                'chunks': sum(len(d['chunks']) for d in current['documents']),
                'source_commit': source_commit, 'working_tree_dirty': dirty,
                'source_tree_sha256': hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
                'source_files_sha256': hashes,
                'scope': 'Corpus-only asset. source_commit is the packaging base commit; dirty work is identified separately.',
                'asset': target.name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                'bytes': target.stat().st_size, 'contains_sessions': False}
    manifest_path = output / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (output / 'SHA256SUMS').write_text(''.join(
        f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n' for path in (target, manifest_path)))
    receipt = {k: v for k, v in manifest.items() if k != 'source_files_sha256'}
    receipt.update({'output': str(output), 'published': False,
                    'release_url': None, 'status': 'prepared', 'restore_verified': False})
    Path('reports/release-preparation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data/backups/ring4-public-corpus.json'))
    parser.add_argument('--output', type=Path, default=Path('dist/corpus-release'))
    args = parser.parse_args()
    prepare(args.source, args.output)
