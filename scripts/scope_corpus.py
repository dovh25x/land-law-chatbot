"""Build a Ring4-only immutable snapshot using existing vectors. No remote mutations."""
import argparse
import hashlib
import json
from pathlib import Path
from landlaw.publication import validate_corpus
from landlaw.store import Store
from landlaw.config import Settings
from pydantic import SecretStr

REMOVED_PROJECTS={'songhong','olympic'}


def scoped_release(original):
    value={k:v for k,v in original.items() if k!='id'}
    value['documents']=[d for d in original['documents'] if d.get('project') not in REMOVED_PROJECTS]
    ids={d['id'] for d in value['documents']}
    for key in ('relations','unresolved_relations'):
        value[key]=[r for r in original.get(key,[]) if not any(str(r.get(end,'')).startswith(('songhong-','olympic-')) for end in ('source_id','target_id'))]
    value['coverage_gaps']=[g for g in original.get('coverage_gaps',[]) if not g['document_id'].startswith(('songhong-','olympic-'))]
    value['scope']='ring4'
    value['id']='corpus-'+hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    validate_corpus(value)
    assert all(r['source_id'] in ids and r['target_id'] in ids for r in value['relations'])
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--sqlite',default='data/ring4.db')
    args=parser.parse_args()
    original=json.loads(args.source.read_text())
    release=scoped_release(original)
    target=Path('data/releases')/(release['id']+'.json')
    target.write_text(json.dumps(release,ensure_ascii=False))
    settings=Settings().model_copy(update={'database_url':SecretStr(''),'sqlite_path':args.sqlite})
    store=Store(settings)
    try:
        if not store.release(release['id'],True):store.stage(release)
        store.publish(release['id'])
        store.backup(Path('data/backups/ring4-public-corpus.json'))
    finally:store.close()
    removed={d['id'] for d in original['documents'] if d.get('project') in REMOVED_PROJECTS}
    for file in ('sources.json','projects.json'):
        path=Path('data')/file;rows=json.loads(path.read_text())
        path.write_text(json.dumps([r for r in rows if r.get('project') not in REMOVED_PROJECTS and r.get('id') not in REMOVED_PROJECTS|removed],ensure_ascii=False,indent=2)+'\n')
    path=Path('data/legal_relations.json')
    rows=json.loads(path.read_text())
    path.write_text(json.dumps([r for r in rows if not any(str(r.get(k,'')).startswith(('songhong-','olympic-')) for k in ('source_id','target_id'))],ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'corpus_id':release['id'],'documents':len(release['documents']),'chunks':sum(len(d['chunks']) for d in release['documents']),'sqlite':args.sqlite}))


if __name__=='__main__':main()
