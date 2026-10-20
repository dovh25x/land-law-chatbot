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
 out=Path('reports/production-finalization-20261020/release-policy-evaluation');out.mkdir(parents=True,exist_ok=True)
 receipt=Path('reports/production-readiness-20261020/natural-attempt-1/isolated-databases.jsonl')
 name=json.loads(receipt.read_text().splitlines()[-1])['database'];assert name.startswith('landlaw_generation_')
 initial=Settings();s=initial.for_operator().model_copy(update={'reports_dir':out,'database_url':SecretStr(make_conninfo(initial.admin_database_url.get_secret_value(),dbname=name)),'admin_database_url':SecretStr('')})
 locked=configuration_fingerprint(s)
 lock=out/'configuration-lock.json'
 if lock.exists():assert json.loads(lock.read_text())['configuration_sha256']==locked
 else:lock.write_text(json.dumps({'configuration_sha256':locked,'reason':'Source-backed vetoes now cover actual agricultural actor/cash loss and actual housing placement-versus-plan substitution; compact synthesis and source order; medium Draft/Verification at same model and fixed token/request/time caps. Entire frozen 32-case cohort measured afresh without imported passes.','model':'openai/gpt-oss-120b','hosting':'Free','authorized_cases':32},indent=2)+'\n')
 (out/'database-reuse.json').write_text(json.dumps({'database':name,'source_receipt':str(receipt),'source_receipt_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),'serving_database_changed':False,'restored_again':False,'scope':'Same isolated immutable corpus; inherited provider cooldown/counters retained.'},indent=2)+'\n')
 with psycopg.connect(s.database_url.get_secret_value(),connect_timeout=15) as c:assert c.execute('SELECT current_database()').fetchone()[0]==name
 store=Store(s);provider=GroqProvider(s,store,usage_scope='operator');generate=provider.generate
 async def guarded(*args,**kwargs):
  assert configuration_fingerprint(s)==locked
  return await generate(*args,**kwargs)
 provider.generate=guarded
 try:
  assert store.release(None,True)['id']=='corpus-a26bc99e541fbbe2'
  for split in ['natural','smoke','supplemental']:
   assert configuration_fingerprint(s)==locked
   if split=='natural':
    await evaluate(s,store,provider,split,concurrency=1,case_ids=['N03'])
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
