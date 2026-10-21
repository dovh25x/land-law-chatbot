"""Compare source admission and probe startup locally; never performs external HTTP."""
import asyncio,hashlib,json,tempfile
from pathlib import Path
from pydantic import SecretStr
from fastapi.testclient import TestClient
import httpx
from landlaw.config import Settings
from landlaw.store import Store
from landlaw.provider import GroqProvider
from landlaw.api import create_app
from landlaw.ops import record_source_review,activate_source_gate
from landlaw.evaluation import configuration_fingerprint
from landlaw.security import utcnow
base=Path('reports/phase2c-current-20261021');old=Path('reports/phase2b-rc-20261021')
cases=json.loads((base/'acceptance-cases-final.json').read_text())
payload=json.load(open('data/staging/phase2c-current/release-v5.json'))
chunks={c['id']:c for d in payload['documents'] for c in d['chunks']}
report={'checked_at':utcnow().isoformat(),'external_llm_requests':0,'scope':'Source admission comparison, not before/after model performance; local API startup is not PostgreSQL or public E2E.'}
with tempfile.TemporaryDirectory(prefix='landlaw-phase2c-status-') as folder:
 settings=Settings(_env_file=None,app_env='development',database_url='',admin_database_url='',groq_api_key='',allow_stale_generation=False,sqlite_path=str(Path(folder)/'before.db'))
 before=Store(settings)
 try:
  original=json.load(open('data/staging/production-backup-check-20261020/release.json'));before.stage(original);before.publish(original['id'])
  for p in sorted((old/'receipts').glob('*.json')):record_source_review(before,p)
  activate_source_gate(before,old/'source-gate.json');release=before.release(None,True)
  rows=[]
  from datetime import date
  for case in cases['cases'][:3]:
   ids=list(dict.fromkeys(c for claim in case['fixture_claims'] for c in claim['citation_ids']))
   reviews=before.scoped_source_reviews(release,[(chunks[c]['document_id'],c,chunks[c]['checksum']) for c in ids],date.fromisoformat(cases['as_of']))
   rows.append({'id':case['id'],'citation_source_states':reviews,'all_required_citations_admitted':all(s=='fresh' for s in reviews.values())})
  report['before_source_admission']=rows
 finally:before.close()
 actual=Settings();settings=actual.model_copy(update={'app_env':'development','database_url':SecretStr(''),'admin_database_url':SecretStr(''),'sqlite_path':str(Path(folder)/'startup.db'),'allow_stale_generation':False})
 store=Store(settings);outbound=[]
 def forbidden(request):
  outbound.append(request.url.host);raise AssertionError('External HTTP is disabled')
 provider=GroqProvider(settings,store,client=httpx.AsyncClient(transport=httpx.MockTransport(forbidden)))
 try:
  store.restore(Path('data/staging/phase2c-current/acceptance-date-fix-backup.json'))
  report['restore_without_receipts_usable']=store.source_gate_status(store.release(None,True))['usable']
  for p in sorted((base/'receipts-final').glob('*.json')):record_source_review(store,p)
  activate_source_gate(store,base/'source-gate-final.json');release=store.release(None,True)
  rows=[]
  for case in cases['cases'][:3]:
   ids=list(dict.fromkeys(c for claim in case['fixture_claims'] for c in claim['citation_ids']))
   reviews=store.scoped_source_reviews(release,[(chunks[c]['document_id'],c,chunks[c]['checksum']) for c in ids],date.fromisoformat(cases['as_of']))
   rows.append({'id':case['id'],'citation_source_states':reviews,'all_required_citations_admitted':all(s=='fresh' for s in reviews.values())})
  report['after_source_admission']=rows
  with TestClient(create_app(settings,store,provider)) as api:
   rows=[]
   for path in ['/healthz','/readyz','/api/v1/status']:
    response=api.get(path);value=response.json();rows.append({'path':path,'status':response.status_code,'metadata':{k:value[k] for k in ['status','database','storage','llm_configured','corpus_release','source_gate','configuration_sha256','source_fresh','generation_available'] if k in value}})
  report.update(storage_backend='isolated_sqlite',corpus_id=release['id'],source_gate=store.source_gate_status(release),startup=rows,outbound_requests=outbound,real_provider_constructed=True,
    sqlite_configuration_sha256=configuration_fingerprint(settings),postgresql_configuration_sha256_planned_only=configuration_fingerprint(settings.model_copy(update={'database_url':SecretStr('postgresql://fingerprint-only')})),
    model=settings.generation_model,embedding=settings.embedding_model)
 finally:asyncio.run(provider.close());store.close()
(base/'scope-and-startup.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'before':[r['all_required_citations_admitted'] for r in report['before_source_admission']],'after':[r['all_required_citations_admitted'] for r in report['after_source_admission']],'HTTP':[r['status'] for r in report['startup']],'outbound':len(outbound)}))
