"""Audit retained fixture evidence against the actual bounded synthesis selection.

No model/database/network calls. A raw-ID fixture can cite a retrieved passage
that the model never receives; do not call that full pipeline acceptance.
"""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
b=Path('reports/phase2c-current-20261021');p=b/'acceptance-context-pack/report.json';report=json.loads(p.read_text());rows=[]
for case in report['cases'][:3]:
 shown=case['synthesis_context'];byid={c['citation_id']:c for c in case['contexts']};available={c['citation_id'] for c in shown};checks=[]
 for cite in case['answer']['citations']:
  original=byid[cite['id']]
  equivalents=[c['citation_id'] for c in shown if c['document_id']==original['document_id']
   and c['locator'].split(' · ')[0]==original['locator'].split(' · ')[0]
   and original['text'] in c['text']]
  checks.append({'citation_id':cite['id'],'same_id_shown':cite['id'] in available,
   'source_text_in_same_document_article_shown':bool(equivalents),'equivalent_prompt_citations':equivalents})
 rows.append({'id':case['id'],'fixture_status':case['answer']['status'],'retrieval_articles_complete':case['all_required_articles_reviewed'],
  'all_cited_ids_shown':all(c['same_id_shown'] for c in checks),
  'all_source_basis_shown_including_parent_equivalence':all(c['source_text_in_same_document_article_shown'] for c in checks),
  'citations':checks,'missing_source_ids':[c['citation_id'] for c in checks if not c['source_text_in_same_document_article_shown']]})
value={'checked_at':datetime.now(timezone.utc).isoformat(),'input_path':str(p),'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
 'scope':'Post-check of real prompt_context selection, not model inference. Same-document/article containment admits parent-equivalent text but does not turn a hidden raw citation ID into a model pass.',
 'external_llm_requests':0,'model_pass':None,'full_pipeline_acceptance_established':False,
 'source_basis_complete_in_synthesis_cases':sum(r['all_source_basis_shown_including_parent_equivalence'] for r in rows),'n':3,'results':rows}
(b/'synthesis-projection-review.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'complete_source_basis':value['source_basis_complete_in_synthesis_cases'],'n':3,'missing':{r['id']:r['missing_source_ids'] for r in rows}},ensure_ascii=False))
