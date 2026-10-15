"""Create a secret-free academic handoff ZIP from committed source only.

Requires an exported public corpus backup and the completed demo recording.
Never adds .env, model caches, private backups, session credentials or git data.
"""
import argparse
import hashlib
import io
import json
import re
from dotenv import dotenv_values
import subprocess
import tarfile
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, default=Path('data/backups/mvp-public-corpus.json'))
    parser.add_argument('--output', type=Path, default=Path('dist/hanoi-land-law-mvp.zip'))
    args = parser.parse_args()
    corpus = json.loads(args.corpus.read_text())
    if corpus.get('format') != 1 or any(k in corpus for k in ('sessions', 'messages', 'traces')):
        raise SystemExit('Only a corpus-only backup can be packaged')
    if len(corpus.get('releases', [])) != 1:
        raise SystemExit('Package must contain exactly the published corpus snapshot')
    video = Path('reports/submission/demo-silent.webm')
    receipt = json.loads(Path('reports/submission/video.json').read_text())
    evaluation = json.loads(Path('reports/submission/evaluation.json').read_text())
    if (evaluation.get('status') != 'reviewed' or len(evaluation.get('results', [])) != 20
            or receipt.get('configuration_sha256') != evaluation.get('identity', {}).get('configuration_sha256')
            or not receipt.get('checks', {}).get('evaluation_matches_active_configuration')
            or not receipt.get('checks', {}).get('configuration_unchanged')):
        raise SystemExit('Video and reviewed evaluation must match the final runtime configuration')
    if receipt.get('status') != 'recorded' or receipt.get('model') != 'openai/gpt-oss-20b' or receipt.get('seconds', 0) < 300:
        raise SystemExit('A successful current Groq demo video is required')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    archive = subprocess.check_output(['git', 'archive', 'HEAD'])
    secrets = [value.encode() for name, value in dotenv_values('.env').items() if value and len(value) >= 12
        and re.search(r'TOKEN|API_KEY|SECRET|PASSWORD|DATABASE_URL|BACKUP_ENCRYPTION_KEY', name)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as target:
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            for member in source:
                if not member.isfile() or member.name == 'reports/submission/package.json':
                    continue
                if Path(member.name).name.startswith('.env') and Path(member.name).name != '.env.example':
                    raise SystemExit('Refusing environment file in tracked archive')
                target.writestr(member.name, source.extractfile(member).read())
        target.write(args.corpus, 'data/demo/corpus-backup.json')
        target.write(video, 'reports/submission/demo-silent.webm')
        target.writestr('SOURCE_COMMIT.txt', commit + '\n')
    with zipfile.ZipFile(args.output) as result:
        if result.testzip() is not None:
            raise SystemExit('ZIP checksum verification failed')
        for item in result.infolist():
            content = result.read(item)
            if any(secret in content for secret in secrets):
                args.output.unlink()
                raise SystemExit('Refusing package: configured secret detected; no value printed')
    report = {'source_commit': commit, 'archive': str(args.output), 'bytes': args.output.stat().st_size,
        'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(), 'contains_secrets': False,
        'corpus_release': corpus['releases'][0]['id'], 'video_model': receipt['model'],
        'scope': 'Committed source, report/slides, evaluation, public corpus-only backup and real demo video. Requires your own Groq key and free model download for local startup.'}
    Path('reports/submission/package.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
