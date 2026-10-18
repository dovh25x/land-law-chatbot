import asyncio,json,tempfile
from pathlib import Path
from pydantic import SecretStr
from landlaw.agent import Plan
from landlaw.config import Settings
from landlaw.provider import Budget,GroqProvider,ProviderUnavailable
from landlaw.security import utcnow
from landlaw.store import Store

async def main():
 report={'checked_at':utcnow().isoformat(),'scope':'One small diagnostic request; not a full legal-answer or throughput benchmark','credential_source':'current Settings configuration; credential never printed or saved','responses':[]}
 with tempfile.TemporaryDirectory(prefix='landlaw-key-probe-') as folder:
  settings=Settings().for_operator().model_copy(update={'database_url':SecretStr(''),'admin_database_url':SecretStr(''),'sqlite_path':str(Path(folder)/'probe.db')})
  store=Store(settings);provider=GroqProvider(settings,store,usage_scope='operator');budget=Budget()
  async def observe(response):
   headers={k:v for k,v in response.headers.items() if k.lower().startswith('x-ratelimit-') or k.lower()=='retry-after'}
   report['responses'].append({'http_status':response.status_code,'quota_headers':headers})
  provider.client.event_hooks.setdefault('response',[]).append(observe)
  try:
   await provider.generate(Plan,'Diagnostic only. Return an empty plan, no tools, no missing facts, out_of_scope false.',{'diagnostic':True},budget,max_attempts=1)
   report['passed']=True
  except Exception as error:
   report.update(passed=False,error_type=type(error).__name__)
  finally:
   report.update(llm_requests=budget.llm_calls,total_tokens=budget.tokens,model=settings.groq_model)
   await provider.close();store.close()
 Path('reports/corpus-remediation-20261018/updated-key-probe-2.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report))
asyncio.run(main())
