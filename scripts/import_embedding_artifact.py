"""Restore checksum-matched vectors from our latest successful Actions artifact."""
import io
import json
import re
import tarfile
import zipfile
from pathlib import Path

import httpx
from dotenv import dotenv_values

from landlaw.ingest import json_write
from landlaw.provider import Gemini
from landlaw.security import digest, utcnow


def main():
    env = dotenv_values('.env')
    root = 'https://api.github.com/repos/dovh25x/land-law-chatbot/actions'
    with httpx.Client(timeout=120, follow_redirects=True,
                      headers={'Authorization': 'Bearer '+env['GITHUB_TOKEN'], 'Accept': 'application/vnd.github+json'}) as c:
        r = c.get(root+'/workflows/embeddings.yml/runs', params={'per_page': 10, 'status': 'success'})
        r.raise_for_status()
        for run in r.json()['workflow_runs']:
            r = c.get(root+f"/runs/{run['id']}/artifacts"); r.raise_for_status()
            artifacts = [a for a in r.json()['artifacts'] if a['name']=='embedding-staging' and not a['expired']]
            if artifacts:
                artifact = artifacts[0]
                break
        else:
            raise SystemExit('No unexpired successful embedding artifact')
        r = c.get(artifact['archive_download_url']); r.raise_for_status()
        if len(r.content) > 40*1024*1024:
            raise SystemExit('Artifact exceeds size limit')
        restored = 0
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for name in z.namelist():
                if not name.endswith('.tar.gz'):
                    continue
                with tarfile.open(fileobj=io.BytesIO(z.read(name)), mode='r:gz') as t:
                    for m in t.getmembers():
                        if not (m.isfile() and re.fullmatch(r'data/staging/corpus-[0-9a-f]{16}\.json',m.name)):
                            continue
                        if m.size > 150*1024*1024:
                            raise SystemExit('Corpus archive exceeds size limit')
                        payload = json.load(t.extractfile(m))
                        if payload.get('embedding_model')!='gemini-embedding-2' or payload.get('embedding_dimensions')!=768:
                            raise SystemExit('Artifact embedding contract mismatch')
                        for doc in payload['documents']:
                            for chunk in doc['chunks']:
                                if digest(chunk['text']) != chunk['checksum']:
                                    raise SystemExit('Chunk checksum mismatch')
                                if not chunk.get('embedding'):
                                    continue
                                values = Gemini.normalize_vector(chunk['embedding'])
                                key = digest(f"embedding-format-v1:gemini-embedding-2:{doc['title']}:{chunk['checksum']}")
                                json_write(Path('data/checkpoints')/f'{key}.json', {'embedding':values})
                                restored += 1
        report = {'checked_at':utcnow().isoformat(),'workflow_url':run['html_url'], 'artifact_id':artifact['id'],
                  'restored_vectors':restored,'source_release':payload['id']}
        json_write(Path('reports/checkpoint-import.json'),report)
        print(json.dumps(report),flush=True)


if __name__=='__main__':
    main()
