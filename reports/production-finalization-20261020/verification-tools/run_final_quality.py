"""Authorized frozen32, immutable cohort, retained isolated PG; no automatic deploy."""
import asyncio,hashlib,json,subprocess
from datetime import timedelta
from pathlib import Path
import psycopg
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint,evaluate,frozen_dataset
from landlaw.provider import GroqProvider
from landlaw.security import utcnow
from landlaw.store import Store

async def main():
 out=Path('reports/production-finalization-20261020/final-quality-evaluation');out.mkdir(parents=True,exist_ok=True)
 receipt=Path('reports/production-readiness-20261020/natural-attempt-1/isolated-databases.jsonl')
 name=json.loads(receipt.read_text().splitlines()[-1])['database'];assert name.startswith('landlaw_generation_')
 initial=Settings();s=initial.for_operator().model_copy(update={'reports_dir':out,'database_url':SecretStr(make_conninfo(initial.admin_database_url.get_secret_value(),dbname=name)),'admin_database_url':SecretStr('')})
 fingerprint=configuration_fingerprint(s);lock=out/'configuration-lock.json'
 if lock.exists():assert json.loads(lock.read_text())['configuration_sha256']==fingerprint
 else:lock.write_text(json.dumps({'configuration_sha256':fingerprint,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'reason':'Combine actual N01 damage-causation, N04 prerequisite evidence and S04 decision-time regressions. Same120B/Free/E5/workflow caps. Fresh frozen32 cohort, no prior pass imported.','authorized_cases':32,'hosting':'Free'},indent=2)+'\n')
 with psycopg.connect(s.database_url.get_secret_value(),connect_timeout=15) as c:assert c.execute('SELECT current_database()').fetchone()[0]==name
 (out/'database-reuse.json').write_text(json.dumps({'database':name,'source_receipt':str(receipt),'source_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),'serving_database_changed':False,'counters_or_cooldown_reset':False},indent=2)+'\n')
 store=Store(s);provider=GroqProvider(s,store,usage_scope='operator');generate=provider.generate;model_calls_allowed=False
 async def guarded(*args,**kwargs):
  assert configuration_fingerprint(s)==fingerprint
  if not model_calls_allowed:raise AssertionError('Guard-only phase may not call Groq')
  return await generate(*args,**kwargs)
 provider.generate=guarded
 async def phase(split,ids,label):
  assert configuration_fingerprint(s)==fingerprint
  report=await evaluate(s,store,provider,split,concurrency=1,case_ids=ids)
  remaining=store.cooldown()
  (out/'operator-cooldown.json').write_text(json.dumps({'not_before':(utcnow()+timedelta(seconds=remaining)).isoformat(),'source':'Actual provider cooldown, retained without reset; minimum request wait does not guarantee whole-turn capacity.'},indent=2)+'\n')
  print(json.dumps({'stage':label,'split':split,'results':report['results'],'cooldown_seconds':remaining}),flush=True)
  return remaining<=60
 guards={'natural':['N07','N08'],'smoke':['S01','S02','S03','S09','S10','S11','S12','S13','S15','S16','S18','S19','S20'],'supplemental':['X04']}
 critical={'natural':['N01','N04'],'smoke':['S04','S06'],'supplemental':['X02','X03']}
 try:
  assert store.release(None,True)['id']=='corpus-a26bc99e541fbbe2'
  for split,ids in guards.items():
   if not await phase(split,ids,'guard_only'):return
  model_calls_allowed=True
  for split,ids in critical.items():
   if not await phase(split,ids,'critical_regressions'):return
  for split in ['natural','smoke','supplemental']:
   cases,_=frozen_dataset(s.data_dir,split);ids=[c['id'] for c in cases if c['id'] not in guards[split]+critical[split]]
   if not await phase(split,ids,'remaining_locked_cases'):return
 finally:await provider.close();store.close()
try:asyncio.run(main())
except Exception as error:
 print(json.dumps({'passed':False,'error_type':type(error).__name__}),flush=True);raise SystemExit(1) from None
