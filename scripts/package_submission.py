"""Package committed academic source and a public corpus-only backup, never .env."""
import io
import json
import hashlib
import subprocess
import tarfile
import zipfile
from pathlib import Path
from dotenv import dotenv_values


def main():
    evaluation=json.loads(Path('reports/submission/evaluation.json').read_text())
    if evaluation['status']!='reviewed' or len(evaluation['results'])!=20:
        raise SystemExit('Twenty executed and reviewed cases are required')
    corpus=Path('data/backups/mvp-public-corpus.json')
    backup=json.loads(corpus.read_text())
    if backup.get('sessions') or backup.get('messages') or backup.get('traces'):
        raise SystemExit('Only a corpus-only backup can be included')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    archive=subprocess.check_output(['git','archive','HEAD'])
    secrets=[v for k,v in dotenv_values('.env').items() if v and len(v)>12 and any(x in k for x in ('KEY','TOKEN','SECRET','DATABASE_URL'))]
    target=Path('dist/hanoi-land-law-mvp.zip');target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            for member in source.getmembers():
                if member.isfile() and member.name!='reports/submission/package.json':
                    content=source.extractfile(member).read()
                    if any(s.encode() in content for s in secrets):raise SystemExit('Secret detected in '+member.name)
                    z.writestr(member.name,content)
        content=corpus.read_bytes()
        if any(s.encode() in content for s in secrets):raise SystemExit('Secret detected in corpus backup')
        z.writestr('data/demo/corpus-backup.json',content)
        z.writestr('SOURCE_COMMIT.txt',commit+'\n')
    with zipfile.ZipFile(target) as z:
        if z.testzip():raise SystemExit('Invalid archive')
    receipt={'source_commit':commit,'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
             'bytes':target.stat().st_size,'scope':'Committed source, twenty-case evaluation, docs, public corpus-only backup. No presentation/video, secrets or private conversations.'}
    Path('reports/submission/package.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
