"""Read-only source worklist. Candidate presence is never legal task coverage."""
import argparse
import hashlib
import json
from pathlib import Path


def inspect(snapshot, requirements):
    docs={d['id']:d for d in snapshot['documents']}
    rows=[]
    operational=[d['id'] for d in docs.values() if d['source_kind'] in {'official_procedure','official_directory'}]
    for requirement in requirements['requirements']:
        present=[identifier for identifier in requirement['candidate_document_ids'] if identifier in docs]
        rows.append({**requirement,'present_candidate_ids':present,
            'missing_candidate_ids':sorted(set(requirement['candidate_document_ids'])-docs.keys()),
            'status':'missing_operational_sources' if requirement['needs_operational_source'] and not operational else 'awaiting_proposition_and_dependency_review',
            'coverage_approved':False})
    return {'corpus_id':snapshot['id'],'requirements':rows,
        'scope':'Document inventory only; no source review, model calls, embedding, database writes or coverage certification.',
        'coverage_approved':False,'operational_documents':operational if rows else []}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--requirements',type=Path,default=Path('data/citizen_source_requirements.json'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('Preserve the previous worklist; choose a new output')
    result=inspect(json.loads(args.snapshot.read_text()),json.loads(args.requirements.read_text()))
    result['snapshot_sha256']=hashlib.sha256(args.snapshot.read_bytes()).hexdigest()
    result['requirements_sha256']=hashlib.sha256(args.requirements.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'requirements':len(result['requirements']),'coverage_approved':False,'model_calls':0}))


if __name__=='__main__':main()
