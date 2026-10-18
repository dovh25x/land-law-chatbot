import json
from pathlib import Path
from datetime import datetime,timezone
from landlaw.ingest import coverage
from landlaw.security import digest,utcnow
root=Path('reports/corpus-remediation-20261018');candidate=json.loads(Path('data/staging/remediation-20261018-attempt-1/candidate.json').read_text());sources=json.loads(Path('data/sources.json').read_text());fetch={r['id']:r for r in json.loads((root/'source-fetch.json').read_text())['results']};relations=json.loads(Path('data/legal_relations.json').read_text())
reviews=[]
for doc in candidate['documents']:
 reviews.append({'document_id':doc['id'],'checksum':doc['checksum'],'snapshot_checked_at':doc['checked_at'],
  'official_url':doc.get('publication_url') or doc['url'],'download_evidence':fetch.get(doc['id']),
  'relations_to_review':[r for r in relations if doc['id'] in (r['source_id'],r['target_id'])],
  'review_status':'pending_fulltext_amendment_and_transition_review',
  'receipt_template':{'document_id':doc['id'],'checksum':doc['checksum'],'checked_at':None,'status':None,'relation_review':None,'evidence_urls':[]}})
(root/'source-review-bundle.json').write_text(json.dumps({'scope':'Checklist only. Byte matches and HTTP success are not amendment/transition review. Null templates cannot be accepted by review-source. No receipt written to any database.','corpus_id':candidate['id'],'sources':reviews},ensure_ascii=False,indent=2)+'\n')
status={'checked_at':utcnow().isoformat(),'candidate_corpus_id':candidate['id'],'coverage_with_final_checker':coverage(candidate),
 'ingest_issues':json.loads(Path('data/staging/remediation-20261018-attempt-1/corpus-coverage.json').read_text())['issues'],
 'freshness_receipts_created':0,'generation_acceptance':'awaiting_full_suite_and_review','publish_allowed':False,'serving_database_changed':False,'release_published':False,'deployed':False,
 'pending_sources':[{'id':s['id'],'raw_paths':s.get('raw_paths',[]),'ocr_review':[x.get('review_status') for x in s.get('ocr_sidecars',[])]} for s in sources if s.get('review_status')!='verified'],
 'additional_missing_endpoint':'qd-20-2022-hanoi',
 'prior_report_correction':'preparation-attempt-1 and evaluation-attempt-1 were started before the final dependency gate; their publication_ready booleans are superseded by coverage_with_final_checker here. Their numerical results remain preserved.'}
(root/'acceptance-status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
