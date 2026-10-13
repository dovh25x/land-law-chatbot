"""Import only fully validated Colab vectors; never publishes a corpus."""
import importlib.util
import json
import sys
from pathlib import Path
import zipfile

from landlaw.ingest import json_write
from landlaw.security import digest, utcnow


def run(bundle, artifact, source, checkpoint_dir=Path('data/checkpoints')):
    spec=importlib.util.spec_from_file_location('colab_worker',Path(__file__).with_name('offline_e5_colab.py'))
    worker=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    summary=worker.validate_output(bundle,artifact)
    data,manifest=worker.load_input(bundle)
    release=json.loads(source.read_text())
    if release['id'] != data['source_release']:
        raise ValueError('Artifact source release differs from staging candidate')
    expected=[{'id':c['id'],'document_id':d['id'],'title':d['title'],'text':c['text'],
               'checksum':c['checksum'],'locator':c['locator'],'page':c.get('page')}
              for d in release['documents'] for c in d['chunks']]
    if expected != data['rows']:
        raise ValueError('Artifact source content/metadata differs from staging candidate')
    with zipfile.ZipFile(artifact) as archive:
        records={r['id']:r for r in (json.loads(line) for line in archive.read('vectors.jsonl').splitlines())}
    model=worker.MODEL['name']
    created=0
    for row in expected:
        vector=records[row['id']]['embedding']
        path=checkpoint_dir/(digest(f"embedding-format-v1:{model}:{row['title']}:{row['checksum']}")+'.json')
        if path.exists():
            if json.loads(path.read_text()) != {'embedding':vector}:
                raise ValueError('An existing checkpoint conflicts with this model/artifact')
        else:
            json_write(path,{'embedding':vector})
            created+=1
    report={'checked_at':utcnow().isoformat(),'status':'imported_not_published','artifact_sha256':digest(artifact.read_bytes()),
            'source_release':release['id'],'model_spec':worker.MODEL,'chunks':len(expected),'created_checkpoints':created,
            'input_sha256':manifest['input_sha256'],'vectors_sha256':summary['vectors_sha256'],
            'colab_run_seconds':summary['run_seconds']}
    json_write(Path('reports/colab-embedding-import.json'),report)
    print(json.dumps(report,ensure_ascii=False))
    return report


if __name__=='__main__':
    run(*(Path(p) for p in sys.argv[1:4]))
