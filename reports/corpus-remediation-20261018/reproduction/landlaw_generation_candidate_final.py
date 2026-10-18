import asyncio,json,tempfile
from pathlib import Path
from pydantic import SecretStr
from landlaw.config import Settings
from landlaw.store import Store
from landlaw.provider import GroqProvider
from landlaw.evaluation import evaluate
async def main():
 output=Path('reports/corpus-remediation-20261018/generation-attempt-2');output.mkdir(exist_ok=False)
 base=Settings().for_operator()
 with tempfile.TemporaryDirectory(prefix='landlaw-generation-candidate-') as folder:
  settings=base.model_copy(update={'database_url':SecretStr(''),'admin_database_url':SecretStr(''),'sqlite_path':str(Path(folder)/'candidate.db'),'reports_dir':output})
  store=Store(settings);store.restore(Path('data/staging/remediation-20261018-attempt-2/candidate-backup.json'))
  provider=GroqProvider(settings,store,usage_scope='operator')
  try:
   for split in ('smoke','supplemental','natural'):
    report=await evaluate(settings,store,provider,split,concurrency=1)
    print(json.dumps({'split':split,'results':report['results'],'run_id':report['run_id']}),flush=True)
  finally:
   await provider.close();store.close()
asyncio.run(main())
