import asyncio,json,tempfile
from pathlib import Path
from pydantic import SecretStr
from landlaw.config import Settings
from landlaw.store import Store
from landlaw.provider import GroqProvider,ProviderUnavailable
from landlaw.evaluation import evaluate
async def main():
 output=Path('reports/corpus-remediation-20261018/generation-attempt-2')
 with tempfile.TemporaryDirectory(prefix='landlaw-deterministic-eval-') as folder:
  settings=Settings().for_operator().model_copy(update={'database_url':SecretStr(''),'admin_database_url':SecretStr(''),'sqlite_path':str(Path(folder)/'evaluation.db'),'reports_dir':output})
  store=Store(settings);store.restore(Path('data/staging/remediation-20261018-attempt-1/candidate-backup.json'));provider=GroqProvider(settings,store,usage_scope='operator')
  async def no_provider(*args,**kwargs):
   raise ProviderUnavailable('Provider calls disabled during observed daily cooldown',retryable=False)
  provider.generate=no_provider
  try:
   report=await evaluate(settings,store,provider,'natural',case_ids=['N07','N08'])
   records=json.loads((output/'runs'/report['run_id']/'records.json').read_text());checked=[r for r in records if r['case_id'] in {'N07','N08'}]
   assert len(checked)==2 and all(r['result']['llm_calls']==0 and r['result']['status'] not in {'limited','error'} for r in checked)
   Path('reports/corpus-remediation-20261018/deterministic-remainder.json').write_text(json.dumps({'passed':True,'case_ids':['N07','N08'],'provider_requests':0,'scope':'Frozen deterministic safety branches only. Provider.generate was disabled to enforce the real daily cooldown; no model answer fabricated. Earlier limited case retained; other five cases remain unexecuted.'},indent=2)+'\n')
  finally:await provider.close();store.close()
asyncio.run(main())
