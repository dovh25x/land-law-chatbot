import asyncio,hashlib,json
from datetime import timedelta
from pathlib import Path
import psycopg
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint,evaluate
from landlaw.provider import GroqProvider
from landlaw.security import utcnow
from landlaw.store import Store

async def main():
 out=Path('reports/production-readiness-20261020/release-candidate-evaluation');assert out.is_dir()
 receipt=Path('reports/production-readiness-20261020/natural-attempt-1/isolated-databases.jsonl')
 name=json.loads(receipt.read_text().splitlines()[-1])['database'];assert name.startswith('landlaw_generation_')
 initial=Settings();s=initial.for_operator().model_copy(update={'reports_dir':out,'database_url':SecretStr(make_conninfo(initial.admin_database_url.get_secret_value(),dbname=name)),'admin_database_url':SecretStr('')})
 locked=configuration_fingerprint(s)
 assert json.loads((out/'configuration-lock.json').read_text())['configuration_sha256']==locked
 (out/'database-reuse.json').write_text(json.dumps({'database':name,'source_receipt':str(receipt),'source_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),'serving_database_changed':False,'restored_again':False,'scope':'Same isolated immutable corpus; inherited provider cooldown/counters retained.'},indent=2)+'\n')
 with psycopg.connect(s.database_url.get_secret_value(),connect_timeout=15) as c:assert c.execute('SELECT current_database()').fetchone()[0]==name
 store=Store(s);provider=GroqProvider(s,store,usage_scope='operator');generate=provider.generate
 async def guarded(*args,**kwargs):
  assert configuration_fingerprint(s)==locked
  return await generate(*args,**kwargs)
 provider.generate=guarded
 try:
  assert store.release(None,True)['id']=='corpus-a26bc99e541fbbe2'
  result=await evaluate(s,store,provider,'natural',concurrency=1,case_ids=['N07','N08'])
  assert configuration_fingerprint(s)==locked
  remaining=store.cooldown()
  (out/'operator-cooldown.json').write_text(json.dumps({'not_before':(utcnow()+timedelta(seconds=remaining)).isoformat(),'source':'Actual provider cooldown retained; all32 authorized; no serving corpus/database mutation.'},indent=2)+'\n')
  print(json.dumps({'split':'natural','results':result['results'],'serving_database_changed':False}),flush=True)
  for split,ids in [('smoke',['S01','S02','S03','S09','S10','S11','S12','S13','S15','S16','S17','S18','S19','S20']),('supplemental',['X04'])]:
   assert configuration_fingerprint(s)==locked
   report=await evaluate(s,store,provider,split,concurrency=1,case_ids=ids)
   print(json.dumps({'split':split,'stage':'guard_cases','results':report['results']}),flush=True)
  for split in ['smoke','supplemental','natural']:
   assert configuration_fingerprint(s)==locked
   report=await evaluate(s,store,provider,split,concurrency=1)
   remaining=store.cooldown()
   (out/'operator-cooldown.json').write_text(json.dumps({'not_before':(utcnow()+timedelta(seconds=remaining)).isoformat(),'source':'Actual provider cooldown retained; expanded 32-case run explicitly authorized.'},indent=2)+'\n')
   print(json.dumps({'split':split,'stage':'all_pending','results':report['results'],'cooldown_seconds':remaining}),flush=True)
   if remaining>60:break
 finally:await provider.close();store.close()

try:asyncio.run(main())
except Exception as error:
 print(json.dumps({'passed':False,'error_type':type(error).__name__}),flush=True)
 raise SystemExit(1) from None
