import json,tempfile,hashlib,asyncio
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
base=Path('reports/phase2b-rc-20261021');outbound=[]
def forbidden(request):
 outbound.append(request.url.host)
 raise AssertionError('External HTTP is disabled for startup validation')
with tempfile.TemporaryDirectory(prefix='landlaw-startup-') as folder:
 actual=Settings()
 settings=actual.model_copy(update={'app_env':'development','database_url':SecretStr(''),'admin_database_url':SecretStr(''),'sqlite_path':str(Path(folder)/'startup.db'),'allow_stale_generation':False})
 store=Store(settings)
 client=httpx.AsyncClient(transport=httpx.MockTransport(forbidden))
 provider=GroqProvider(settings,store,client=client)
 try:
  store.restore(base/'final-policy-replay/corpus-with-source-gate.json')
  for path in sorted((base/'receipts').glob('*.json')):record_source_review(store,path)
  activate_source_gate(store,base/'source-gate.json')
  with TestClient(create_app(settings,store,provider)) as api:
   rows=[]
   for path in ['/healthz','/readyz','/api/v1/status']:
    response=api.get(path);value=response.json()
    rows.append({'path':path,'status':response.status_code,'metadata':{k:value[k] for k in ['status','database','storage','llm_configured','corpus_release','source_gate','configuration_sha256','source_fresh','generation_available'] if k in value}})
  report={'checked_at':utcnow().isoformat(),'storage_backend':'isolated_sqlite','real_provider_class_constructed':True,'external_transport_disabled':True,'outbound_requests':outbound,'llm_generation_calls':0,'sqlite_configuration_sha256':configuration_fingerprint(settings),'postgresql_configuration_sha256_planned_only':configuration_fingerprint(settings.model_copy(update={'database_url':SecretStr('postgresql://fingerprint-only')})),'model':settings.generation_model,'embedding_model':settings.embedding_model,'rows':rows,'scope':'Local API startup with the configured provider identity and an HTTP transport that rejects every external call. Not Groq connectivity, container image or PostgreSQL verification.'}
  (base/'backend-startup.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps({'HTTP':[r['status'] for r in rows],'external_requests':len(outbound),'fingerprints':{k:v for k,v in report.items() if 'configuration_sha256' in k}}))
 finally:
  asyncio.run(provider.close());store.close()
