import asyncio,json,uuid
from pathlib import Path
from psycopg.conninfo import make_conninfo
from pydantic import SecretStr
from landlaw.agent import Agent
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint,frozen_dataset,preserve_attempt,validate_suite_corpus
from landlaw.models import ChatRequest
from landlaw.provider import GroqProvider
from landlaw.security import new_token
from landlaw.store import Store

async def main():
    out=Path('reports/production-readiness-20261020/release-candidate-evaluation')
    name=json.loads(Path('reports/production-readiness-20261020/natural-attempt-1/isolated-databases.jsonl').read_text().splitlines()[-1])['database']
    initial=Settings();s=initial.for_operator().model_copy(update={'reports_dir':out,'database_url':SecretStr(make_conninfo(initial.admin_database_url.get_secret_value(),dbname=name)),'admin_database_url':SecretStr('')})
    locked=json.loads((out/'configuration-lock.json').read_text())['configuration_sha256']
    assert configuration_fingerprint(s)==locked
    store=Store(s);provider=GroqProvider(s,store,usage_scope='operator')
    attempts=0
    async def never_generate(*args,**kwargs):
        nonlocal attempts
        attempts+=1
        raise AssertionError('Guard check attempted generation; do not treat it as a completed case')
    provider.generate=never_generate
    async def emit(_):pass
    try:
        release=store.release(None,True);assert release['id']=='corpus-a26bc99e541fbbe2'
        for split,chosen in [('smoke',['S18','S19','S20']),('supplemental',['X04'])]:
            cases,_=frozen_dataset(s.data_dir,split);validate_suite_corpus(s.data_dir,split,cases,store,release)
            run=next((out/'runs').glob('*-'+split+'-*-agentic'))
            records=json.loads((run/'records.json').read_text()) if (run/'records.json').exists() else []
            for case in [c for c in cases if c['id'] in chosen]:
                if any(r['case_id']==case['id'] for r in records):continue
                assert configuration_fingerprint(s)==locked
                sid=str(uuid.uuid4());store.create_session(sid,new_token())
                a=await Agent(store,provider).run(ChatRequest(session_id=sid,message=case['question'],project='ring4' if case.get('project')=='ring4' else None,history=case.get('history',[]),as_of=case['as_of'],mode='agentic'),emit,release['id'])
                assert a.llm_calls==0 and attempts==0
                r={'case_id':case['id'],'mode':'agentic','answer_origin':'deterministic','evaluation_context':[],
                   'execution_control':'Zero-generation guard check; provider.generate prohibited; inherited provider cooldown/counters unchanged. Only evaluator inter-turn model wait is inapplicable because no model request is permitted.',
                   'result':a.model_dump(mode='json')}
                preserve_attempt(run/'attempts',r)
                records.append(r);(run/'records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
                print(json.dumps({'case_id':case['id'],'status':a.status,'llm_calls':0,'generation_attempted':False}),flush=True)
        assert attempts==0
    finally:await provider.close();store.close()

try:asyncio.run(main())
except Exception as error:
    print(json.dumps({'passed':False,'error_type':type(error).__name__}));raise SystemExit(1) from None
