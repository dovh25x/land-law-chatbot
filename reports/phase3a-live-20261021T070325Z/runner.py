"""Authorized C01/C02/C03 pilot. No runtime edits, resume, extra attempts or judge.

The transport reserves full UTF-8 JSON bytes + 4096 template/schema overhead +
max_completion_tokens before EVERY wire send, including retries. Observed usage
replaces that reservation only when present/valid. Unknown usage keeps it.
"""
import argparse
import asyncio
import copy
import hashlib
import json
import sys
import tempfile
import time
from datetime import date,datetime,timedelta,timezone
from pathlib import Path

import httpx
from pydantic import SecretStr
from landlaw.agent import Agent,quote_matches
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.local_embedding import Encoder,MODEL
from landlaw.models import ChatRequest
from landlaw.ops import activate_source_gate,record_source_review
from landlaw.provider import GroqProvider,BudgetExceeded,ProviderUnavailable
from landlaw.store import Store,RateLimited

ROOT=Path.cwd()
OUT=Path(__file__).parent
PHASE2D=Path('reports/phase2d-synthesis-20261021')
CASES=Path('reports/phase2c-current-20261021/acceptance-cases-final.json')
CORPUS=Path('data/staging/phase2c-current/release-v5.json')
POLICY=Path('reports/phase2c-current-20261021/source-gate-final.json')
RECEIPTS=Path('reports/phase2c-current-20261021/receipts-final')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    path=OUT/path;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


class PilotBudget(BudgetExceeded):pass


class TokenGate:
    """An unknown request is charged its entire conservative reservation."""
    def __init__(self):
        self.requests=0;self.case_requests={};self.charged=0;self.observed=0;self.unknown=0
    def reserve(self,case,wire_bytes,max_output):
        upper=wire_bytes+4096+max_output
        if self.requests>=18 or self.case_requests.get(case,0)>=6:
            raise PilotBudget('pilot_request_cap')
        if self.charged+upper>60000:raise PilotBudget('pilot_token_cap')
        self.requests+=1;self.case_requests[case]=self.case_requests.get(case,0)+1
        self.charged+=upper
        return upper
    def settle(self,reserved,usage):
        value=usage.get('total_tokens') if isinstance(usage,dict) else None
        if type(value)!=int or value<0:
            self.unknown+=1;return
        if value>reserved:raise PilotBudget('usage_exceeded_conservative_bound')
        self.charged+=value-reserved;self.observed+=value
    def dump(self):return {'wire_requests':self.requests,'per_case_requests':self.case_requests,
        'tokens_observed':self.observed,'tokens_charged_including_unknown':self.charged,
        'unknown_usage_requests':self.unknown,'hard_token_cap':60000}


def requirements(payload,expected):
    rows=[]
    for req in expected:
        matches=[e['citation_id'] for e in payload.get('evidence',[]) if e['document_id']==req['document_id']
            and e['locator'].split(' · ')[0]==req['locator'] and quote_matches(req['text'],e.get('text',''))]
        rows.append({**{k:v for k,v in req.items() if k!='text'},'present':bool(matches),'wire_aliases':matches})
    return rows


class ControlledTransport(httpx.AsyncBaseTransport):
    def __init__(self,guard,gate,context,secrets,underlying=None):
        self.guard,self.gate,self.context,self.secrets=guard,gate,context,[s for s in secrets if s and len(s)>=12]
        self.real=underlying or httpx.AsyncHTTPTransport(retries=0)
    async def aclose(self):await self.real.aclose()
    async def handle_async_request(self,request):
        self.guard()
        assert str(request.url)=='https://api.groq.com/openai/v1/chat/completions' and request.method=='POST'
        body=json.loads(request.content);payload=json.loads(body['messages'][-1]['content'])
        ctx=self.context;case=ctx['case'];schema=body['response_format']['json_schema']['name']
        assert body['model']=='openai/gpt-oss-120b' and body['temperature']==0
        assert body['max_completion_tokens']==2048 and body.get('tool_choice')=='none'
        assert schema in {'Plan','Draft','Verification'}
        assert payload['question']==case['question'] and not payload.get('history')
        assert not any(secret in request.content.decode() for secret in self.secrets)
        assert not any(k in payload for k in ('expected_answer','fixture_claims','gold_answers','releases'))
        assert len(payload.get('evidence',[]))<=16
        if ctx['store'].cooldown():raise RateLimited(ctx['store'].cooldown(),source='provider')
        check=requirements(payload,ctx['expected']) if schema=='Draft' else []
        state=ctx.get('state',{})
        snapshot=copy.deepcopy(state.get('synthesis_sources',{}))
        if schema=='Draft':
            assert len(json.dumps([payload['evidence'],payload['documents']],ensure_ascii=False,separators=(',',':')))<=7000
            assert len(snapshot)==len(payload['evidence'])
            assert all(e['text']==s['text'] for e,s in zip(payload['evidence'],snapshot.values()))
        # Only sources actually exposed to synthesis may supply verifier proof.
        if schema=='Verification':
            selected=[e for e in state['evidence'] if e.chunk.id in {c for claim in state['draft'].claims for c in claim.citation_ids}]
            alias={f'C{i+1}':e.chunk.id for i,e in enumerate(selected) if e.chunk.id in snapshot}
            assert all(e['citation_id'] in alias for e in payload.get('evidence',[]))
            assert all(s['citation_id'] in alias and quote_matches(s['quote'],snapshot[alias[s['citation_id']]]['text'])
                       for s in payload.get('source_spans',[]))
        try:reserved=self.gate.reserve(case['id'],len(request.content),body['max_completion_tokens'])
        except PilotBudget as exc:
            ctx['stop_reason']=str(exc)
            save(Path(case['id'])/'blocked-request.json',{'reason':str(exc),'wire_bytes':len(request.content),
                'required_reservation':len(request.content)+4096+2048,'budget':self.gate.dump(),'schema':schema})
            raise
        ordinal=self.gate.requests
        folder=Path(case['id'])/'wire'/f'{ordinal:02d}'
        save(folder/'request.json',body)  # Deliberately no HTTP headers.
        save(folder/'source-state.json',{'schema':schema,'retrieved_sources':state.get('retrieval_diagnostics',{}),
            'retained_sources':[{'id':e.chunk.id,'document_id':e.document.id,'locator':e.chunk.locator,'checksum':e.chunk.checksum}
                for e in state.get('evidence',[])], 'admitted_sources':sorted(state.get('admitted_source_ids',[])),
            'synthesis_sources':snapshot,'diagnostics':state.get('synthesis_diagnostics',{}),
            'required_evidence_checks':check,'reservation_tokens':reserved,'wire_bytes':len(request.content)})
        start=time.monotonic()
        try:
            response=await self.real.handle_async_request(request)
            await response.aread()
        except BaseException as exc:
            self.gate.settle(reserved,{})
            ctx['stop_reason']='timeout_or_transport_error'
            save(folder/'response.json',{'exception_type':type(exc).__name__,'unknown_usage_reservation_kept':reserved,
                'latency_ms':round((time.monotonic()-start)*1000)})
            save(Path('budget.json'),self.gate.dump())
            raise
        try:raw=response.json()
        except ValueError:raw={}
        usage=raw.get('usage',{})
        self.gate.settle(reserved,usage)
        # Keep visible raw response content, never hidden reasoning or auth data.
        visible={k:raw[k] for k in ('id','object','created','model','usage','system_fingerprint') if k in raw}
        visible['choices']=[{'index':c.get('index'),'finish_reason':c.get('finish_reason'),
            'message':{k:c.get('message',{}).get(k) for k in ('role','content')}} for c in raw.get('choices',[])]
        if response.status_code>=400:
            visible['error']={k:raw.get('error',{}).get(k) for k in ('type','code','message')}
        serialized=json.dumps(visible,ensure_ascii=False)
        for secret in self.secrets:serialized=serialized.replace(secret,'[REDACTED]')
        visible=json.loads(serialized)
        record={'status_code':response.status_code,'schema':schema,'body':visible,
            'raw_body_sha256':hashlib.sha256(response.content).hexdigest(),
            'hidden_reasoning_not_persisted':True,'latency_ms':round((time.monotonic()-start)*1000),
            'headers':{k:v for k,v in response.headers.items() if k.startswith('x-ratelimit-') or k in {'retry-after','x-request-id'}},
            'reservation_tokens':reserved,'usage':usage,'budget_after':self.gate.dump()}
        save(folder/'response.json',record);save(Path('budget.json'),self.gate.dump())
        ctx.setdefault('responses',[]).append(record)
        return response


async def run():
    manifest=json.loads((PHASE2D/'release-manifest.json').read_text())
    baseline=json.loads((OUT/'baseline.json').read_text())
    all_cases=json.loads(CASES.read_text());cases=all_cases['cases'][:3]
    assert [c['id'] for c in cases]==['C01','C02','C03']
    expected=json.loads((PHASE2D/'acceptance-locked/required-evidence.json').read_text())
    files=[*map(Path,baseline['phase2d_source_files']),CORPUS,CASES,POLICY,*sorted(RECEIPTS.glob('*.json')),Path(__file__)]
    locked={str(p):sha(p) for p in files}
    assert sha(CORPUS)==manifest['corpus']['payload_sha256']
    assert all(sha(p)==h for p,h in baseline['phase2d_source_files'].items())
    raw_settings=Settings()
    secrets=[v.get_secret_value() for v in raw_settings.__dict__.values() if isinstance(v,SecretStr)]
    for name,checksum in [('model_quantized.onnx',MODEL['onnx_sha256']),('sentencepiece.bpe.model',MODEL['tokenizer_sha256'])]:
        assert Encoder.file_sha(raw_settings.local_embedding_model_dir/name)==checksum
    with tempfile.TemporaryDirectory(prefix='landlaw-phase3a-') as folder:
        settings=raw_settings.model_copy(update={'app_env':'development','database_url':SecretStr(''),
            'admin_database_url':SecretStr(''),'allow_stale_generation':False,'sqlite_path':str(Path(folder)/'pilot.db'),'reports_dir':OUT})
        runtime=configuration_fingerprint(settings)
        assert runtime==manifest['runtime']['sqlite_fingerprint_verified'],'candidate_runtime_mismatch'
        assert settings.generation_model=='openai/gpt-oss-120b' and settings.turn_timeout_seconds==90
        assert settings.groq_api_key.get_secret_value(),'Groq credentials not configured'
        store=Store(settings)
        gate=TokenGate();ctx={};records=[]
        def unchanged():
            assert configuration_fingerprint(settings)==runtime
            assert all(sha(p)==h for p,h in locked.items()),'locked_inputs_changed'
            assert store.source_gate_status(store.release(None,True))['policy_sha256']==manifest['source_policy']['canonical_sha256']
        try:
            store.stage(json.loads(CORPUS.read_text()));store.publish(manifest['corpus']['id'])
            for p in sorted(RECEIPTS.glob('*.json')):record_source_review(store,p)
            activate_source_gate(store,POLICY)
            assert store.source_gate_status(store.release(None,True))['usable']
            # Inherit operator cooldown receipts, without opening any serving DB.
            cooldowns=[]
            for path in Path('reports').glob('**/operator-cooldown.json'):
                if OUT in path.parents:continue
                try:
                    stamp=json.loads(path.read_text()).get('not_before')
                    if stamp and datetime.fromisoformat(stamp)>datetime.now(timezone.utc):cooldowns.append(stamp)
                except (ValueError,TypeError):raise RuntimeError('Invalid inherited cooldown receipt') from None
            if cooldowns:store.set_cooldown(max(0,(max(datetime.fromisoformat(s) for s in cooldowns)-datetime.now(timezone.utc)).total_seconds()))
            save(Path('configuration-lock.json'),{'head':baseline['head'],'phase2d_candidate_identity':manifest['candidate_identity_sha256'],
                'phase2d_source_tree_sha256':manifest['git']['source_tree_sha256'],'runtime_fingerprint':runtime,
                'corpus_id':manifest['corpus']['id'],'corpus_checksum':sha(CORPUS),'source_policy':manifest['source_policy'],
                'input_sha256':locked,'model':settings.generation_model,'temperature':0,'max_completion_tokens':2048,
                'reasoning':'medium for Draft/Verification; low for Plan','storage':'isolated temporary SQLite',
                'requests_per_case':6,'requests_total':18,'tokens_total_hard_cap':60000,'seconds_per_case':90,
                'reservation':'UTF-8 request JSON bytes +4096 framing/schema allowance +max_completion_tokens',
                'inherited_active_cooldowns':cooldowns,'api_key_recorded':False,
                'candidate_local_override':{'allow_stale_generation':False},'environment_default_allow_stale':raw_settings.allow_stale_generation})
            # Exclusive durable marker forbids automatic second invocation.
            with (OUT/'LIVE_STARTED.json').open('x') as f:json.dump({'started_at':datetime.now(timezone.utc).isoformat(),'case_ids':['C01','C02','C03']},f)
            transport=ControlledTransport(unchanged,gate,ctx,secrets)
            client=httpx.AsyncClient(transport=transport,timeout=25)
            provider=GroqProvider(settings,store,client=client,usage_scope='operator')
            try:
                for index,case in enumerate(cases):
                    unchanged();ctx.clear();ctx.update(case=case,expected=expected[case['id']],store=store)
                    (OUT/case['id']).mkdir(exist_ok=False)
                    if store.cooldown():
                        records.append({'id':case['id'],'operational_status':'INCOMPLETE','reason':'inherited_or_remaining_cooldown','attempt_started':False});break
                    start=time.monotonic();capture={};events=[]
                    class ObservedAgent(Agent):
                        async def tools(self,state):
                            value=await super().tools(state)
                            capture.setdefault('retrieval_rounds',[]).append({'round':value['rounds'],
                                'all_candidates':copy.deepcopy(value.get('retrieval_diagnostics',{})),
                                'retained_context':self.context(value)})
                            return value
                        async def synthesize(self,state):
                            ctx['state']=state;return await super().synthesize(state)
                        async def verify(self,state):
                            ctx['state']=state;value=await super().verify(state)
                            capture.setdefault('verifications',[]).append({'draft':value['draft'].model_dump(mode='json'),
                                'verdict':value['verification'].model_dump(mode='json'),'rounds':value['rounds'],'repairs':value['repairs']})
                            return value
                        async def finish(self,state):
                            value=await super().finish(state)
                            capture.update(final_draft=value['draft'].model_dump(mode='json'),
                                final_verdict=value['verification'].model_dump(mode='json'),
                                final_diagnostics=copy.deepcopy(value.get('synthesis_diagnostics',{})),
                                final_synthesis_sources=copy.deepcopy(value.get('synthesis_sources',{})))
                            return value
                    async def emit(event):events.append(event.model_dump(mode='json'))
                    save(Path(case['id'])/'attempt-start.json',{'started_at':datetime.now(timezone.utc).isoformat(),
                        'question':case['question'],'as_of':all_cases['as_of'],'attempt':1,'history':[]})
                    try:
                        answer=await ObservedAgent(store,provider).run(ChatRequest(session_id='0'*36,
                            message=case['question'],as_of=date.fromisoformat(all_cases['as_of'])),emit)
                        result=answer.model_dump(mode='json')
                        operational='COMPLETE'
                        reason=None
                        if result['status'] in {'limited','error'}:
                            operational='INCOMPLETE';reason=ctx.get('stop_reason') or result['status']
                        record={'id':case['id'],'attempt_started':True,'operational_status':operational,'reason':reason,
                            'answer':result,'elapsed_ms':round((time.monotonic()-start)*1000),
                            'wire_requests':gate.case_requests.get(case['id'],0),'events':events,**capture}
                    except Exception as exc:
                        record={'id':case['id'],'attempt_started':True,'operational_status':'INCOMPLETE',
                            'reason':ctx.get('stop_reason') or type(exc).__name__,
                            'elapsed_ms':round((time.monotonic()-start)*1000),'wire_requests':gate.case_requests.get(case['id'],0),
                            'events':events,**capture}
                    save(Path(case['id'])/'attempt.json',record);records.append(record)
                    save(Path('execution-progress.json'),{'cases':records,'budget':gate.dump()})
                    if record['operational_status']=='INCOMPLETE':break
            finally:await provider.close()
            for case in cases[len(records):]:records.append({'id':case['id'],'attempt_started':False,
                'operational_status':'INCOMPLETE','reason':'not_started_after_prior_operational_stop'})
            unchanged()
            remaining=store.cooldown()
            save(Path('operator-cooldown.json'),{'not_before':(datetime.now(timezone.utc)+timedelta(seconds=remaining)).isoformat(),
                'source':'Groq Retry-After inherited/observed; not application quota'})
            save(Path('execution.json'),{'cases':records,'budget':gate.dump(),'runtime_unchanged':True,
                'locked_inputs_unchanged':all(sha(p)==h for p,h in locked.items()),'runtime_fingerprint':runtime,
                'finished_at':datetime.now(timezone.utc).isoformat(),'serving_database_touched':False,'S06':'FAIL_UNCHANGED'})
            print(json.dumps({'cases':[{'id':r['id'],'operational':r['operational_status'],
                'answer_status':r.get('answer',{}).get('status'),'wire_requests':r.get('wire_requests',0)} for r in records],
                'budget':gate.dump()},ensure_ascii=False),flush=True)
        finally:store.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true');args=parser.parse_args()
    if not args.live:raise SystemExit('Explicit --live is required; no API called')
    asyncio.run(run())
