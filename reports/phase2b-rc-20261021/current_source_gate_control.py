import asyncio,json,tempfile,hashlib
from pathlib import Path
from landlaw.agent import Agent
from landlaw.config import Settings
from landlaw.local_embedding import Encoder
from landlaw.store import Store
from landlaw.models import ChatRequest
from landlaw.ops import record_source_review,activate_source_gate
from landlaw.security import local_date,utcnow
from landlaw.evaluation import configuration_fingerprint
from scripts.verify_source_gate_candidate import OfflineProvider
base=Path('reports/phase2b-rc-20261021')
async def main():
 with tempfile.TemporaryDirectory(prefix='landlaw-current-source-') as folder:
  settings=Settings(_env_file=None,app_env='development',database_url='',admin_database_url='',groq_api_key='',allow_stale_generation=False,sqlite_path=str(Path(folder)/'local.db'))
  store=Store(settings)
  try:
   store.restore(base/'final-policy-replay/corpus-with-source-gate.json')
   for p in sorted((base/'receipts').glob('*.json')):record_source_review(store,p)
   activate_source_gate(store,base/'source-gate.json');release=store.release(None,True)
   capture={}
   class RecordingAgent(Agent):
    async def finish(self,state):
     capture.update(contexts=self.context(state),draft=state['draft'].model_dump(mode='json'),verifier=state['verification'].model_dump(mode='json'))
     return await super().finish(state)
   provider=OfflineProvider(settings,Encoder(Path('models/e5')));agent=RecordingAgent(store,provider)
   async def emit(_):pass
   question='Quyết định 56/2024/QĐ-UBND Hà Nội hiện còn hiệu lực không, văn bản nào thay thế?'
   result=await agent.run(ChatRequest(session_id='0'*36,message=question,as_of=local_date()),emit)
   report={'checked_at':utcnow().isoformat(),'case':'DEMO-CURRENT-SOURCE-FACT','frozen_suite_case':False,'question':question,'as_of':str(local_date()),'whole_corpus_fresh':store.source_fresh(release),'source_gate':store.source_gate_status(release),'configuration_sha256':configuration_fingerprint(settings),'answer':result.model_dump(mode='json'),'external_llm_requests':0,'scope':'Current-day source-gate positive control, not a new benchmark or generated answer.',**capture}
   (base/'current-source-gate-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
   print(json.dumps({'status':result.status,'citations':len(result.citations),'llm_calls':result.llm_calls,'whole_corpus_fresh':report['whole_corpus_fresh']}))
  finally:store.close()
asyncio.run(main())
