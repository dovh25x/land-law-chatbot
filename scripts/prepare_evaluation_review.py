"""Prepare canonical source/rubric bundles; never score or certify answers."""
import argparse
import hashlib
import json
from pathlib import Path

from landlaw.evaluation import dataset


def prepare(records, cases, release):
    cases={case['id']:case for case in cases}
    sources={chunk['id']:(document,chunk) for document in release['documents'] for chunk in document['chunks']}
    bundles=[]
    for record in records:
        case=cases.get(record['case_id'])
        if case is None or record['mode'] not in {'baseline','agentic'}:
            raise ValueError('Unknown case or mode')
        result=record['result']
        if result.get('corpus_release')!=release['id']:
            raise ValueError('Result corpus differs from canonical sources')
        for cid in case.get('gold_chunk_ids',[]):
            if cid not in sources:
                raise ValueError('Missing canonical reference source')
        for cid in set(case.get('gold_chunk_ids',[]))|{c['id'] for c in result.get('citations',[])}:
            if cid in sources and hashlib.sha256(sources[cid][1]['text'].encode()).hexdigest()!=sources[cid][1]['checksum']:
                raise ValueError('Canonical source checksum mismatch')
        citations={}
        for citation in result.get('citations',[]):
            source=sources.get(citation['id'])
            if (not source or source[0]['id']!=citation['document_id'] or source[1]['text']!=citation['excerpt']
                    or citation['id'] not in result.get('evidence_chunk_ids',[])):
                raise ValueError('Citation source mismatch')
            document,chunk=source
            citations[citation['id']]={'document_id':document['id'],'number':document.get('document_number'),
                'kind':document['source_kind'],'effective_from':document.get('effective_from'),
                'effective_to':document.get('effective_to'),'locator':chunk['locator'],
                'text':chunk['text'],'checksum':chunk['checksum'],'url':document['url']}
        for claim in result.get('verified_claims',[]):
            if not claim['citation_ids'] or not set(claim['citation_ids'])<=citations.keys():
                raise ValueError('Claim citation mismatch')
        checksum=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        allowed=case.get('allowed_statuses') or ([case['expected_status']] if case.get('expected_status') else [])
        bundles.append({'case_id':case['id'],'mode':record['mode'],'result_sha256':checksum,
            'question':case['question'],'history':case.get('history',[]),'as_of':str(result['as_of']),
            'critical':case.get('critical',False),'rubric':case.get('rubric',[]),'source_review':case.get('source_review',''),
            'forbidden_claims':case.get('forbidden_claims',[]),'allowed_statuses':allowed,
            'observed_status':result['status'],'status_rubric_issue':bool(allowed and result['status'] not in allowed),
            'displayed_answer':result['content'],'claims':result.get('verified_claims',[]),
            'citations':citations,'gold_sources':[{k:c[k] for k in ('id','document_id','locator','text','checksum')}
                for cid in case.get('gold_chunk_ids',[]) if (source:=sources.get(cid)) for c in [source[1]]],
            'review_status':'awaiting_source_review','scope':'Canonical source/rubric bundle only; no automatic pass or independent legal certification.'})
    return bundles


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records',type=Path,required=True);parser.add_argument('--release',type=Path,required=True)
    parser.add_argument('--suite',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    bundles=prepare(json.loads(args.records.read_text()),dataset(args.suite),json.loads(args.release.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text('\n'.join(json.dumps(item,ensure_ascii=False) for item in bundles)+'\n')
    print(json.dumps({'prepared_source_review_bundles':len(bundles),'auto_scored':False,'output':str(args.output)}))


if __name__=='__main__':main()
