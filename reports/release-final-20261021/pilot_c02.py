"""One authorized C02 attempt, independent 25k allocation; old attempts immutable.

Default mode only serializes/preflights offline. --live requires the user's
confirmed Groq Free account, a complete source context and an exclusive marker.
All DB writes use temporary SQLite; no judge outside the normal pipeline.
"""
import argparse
import ast
import asyncio
import copy
import hashlib
import json
import math
import tempfile
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
from landlaw.agent import Agent, quote_matches
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.local_embedding import Encoder, MODEL
from landlaw.models import ChatRequest, Draft
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.provider import GroqProvider, ProviderUnavailable, SYSTEM_BOUNDARY
from landlaw.request_budget import RequestBudget
from landlaw.store import Store
from pydantic import SecretStr

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent/'pilot-C02'
LEGAL = ROOT/'reports/phase2c-current-20261021'
CORPUS = ROOT/'data/staging/phase2c-current/release-v5.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    target = OUT/name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def required_checks(payload, expected):
    return [{'document_id': r['document_id'], 'locator': r['locator'], 'present': any(
        e['document_id'] == r['document_id'] and e['locator'].split(' · ')[0] == r['locator']
        and quote_matches(r['text'], e.get('text','')) for e in payload.get('evidence', []))}
        for r in expected]


async def run(live=False):
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'LIVE_STARTED.json').exists():
        raise ValueError('The sole attempt has already started; do not rerun')
    case_data = json.loads((LEGAL/'acceptance-cases-final.json').read_text())
    case = next(c for c in case_data['cases'] if c['id'] == 'C02')
    expected = json.loads((ROOT/'reports/phase2d-synthesis-20261021/acceptance-locked/required-evidence.json').read_text())['C02']
    prior = json.loads((ROOT/'reports/phase3b-reliability-20261021T073924Z/release-manifest.json').read_text())
    policy = LEGAL/'source-gate-final.json'
    receipts = sorted((LEGAL/'receipts-final').glob('*.json'))
    paths = [CORPUS, LEGAL/'acceptance-cases-final.json', policy, *receipts,
             *sorted((ROOT/'backend/landlaw').glob('*.py')),
             ROOT/'data/legal_relations.json', Path(__file__)]
    locked = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    assert sha(CORPUS) == prior['corpus']['payload_sha256']
    raw = Settings()
    secrets = [v.get_secret_value() for v in raw.__dict__.values() if isinstance(v, SecretStr)]
    settings = raw.model_copy(update={'app_env':'development', 'database_url':SecretStr(''),
        'admin_database_url':SecretStr(''), 'groq_api_key':raw.groq_api_key if live else SecretStr('offline-placeholder'),
        'allow_stale_generation':False, 'reports_dir':OUT})
    fp = configuration_fingerprint(settings)
    assert fp == prior['runtime']['sqlite_fingerprint_verified']
    assert settings.generation_model == 'openai/gpt-oss-120b' and settings.turn_timeout_seconds == 90
    for name, checksum in [('model_quantized.onnx',MODEL['onnx_sha256']), ('sentencepiece.bpe.model',MODEL['tokenizer_sha256'])]:
        assert Encoder.file_sha(settings.local_embedding_model_dir/name) == checksum
    payload = next(r['synthesis_payload'] for r in json.loads((ROOT/'reports/phase3b-reliability-20261021T073924Z/synthesis-final/report.json').read_text())['cases'] if r['id']=='C02')
    assert payload['question'] == case['question'] and all(r['present'] for r in required_checks(payload,expected))
    instructions = [ast.literal_eval(n.args[1]) for n in ast.walk(ast.parse((ROOT/'backend/landlaw/agent.py').read_text()))
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='generate'
        and n.args and isinstance(n.args[0],ast.Name) and n.args[0].id=='Draft']
    assert len(instructions)==1
    captured = {}
    class CaptureOnly(Exception):
        pass
    class NoIO:
        async def post(self, url, *, headers, json):
            captured.update(json)
            raise CaptureOnly
        async def aclose(self):
            pass
    with tempfile.TemporaryDirectory(prefix='landlaw-final-c02-') as temp:
        settings = settings.model_copy(update={'sqlite_path':str(Path(temp)/'pilot.db')})
        store = Store(settings)
        try:
            store.stage(json.loads(CORPUS.read_text()))
            store.publish(prior['corpus']['id'])
            for receipt in receipts:
                record_source_review(store, receipt)
            activate_source_gate(store, policy)
            assert store.source_gate_status(store.release(None,True))['usable']
            provider = GroqProvider(settings,store,client=NoIO(),usage_scope='operator')
            try:
                try:
                    await provider._groq_generate(Draft, {'systemInstruction':{'parts':[{'text':SYSTEM_BOUNDARY+instructions[0]}]},
                        'contents':[{'parts':[{'text':json.dumps(payload,ensure_ascii=False,separators=(',',':'))}]}],
                        'generationConfig':{'claimPolicy':payload.get('claim_policy')}})
                except CaptureOnly:
                    pass
            finally:
                await provider.close()
            initial = RequestBudget(max_tokens=25000,max_requests=6)
            initial.reserve(captured)
            cooldowns = []
            for file in (ROOT/'reports').glob('**/operator-cooldown.json'):
                stamp = json.loads(file.read_text()).get('not_before')
                if stamp and datetime.fromisoformat(stamp)>datetime.now(UTC):
                    cooldowns.append(stamp)
            latest_headers = json.loads((ROOT/'reports/phase3a-live-20261021T070325Z/C01/wire/03/response.json').read_text())['headers']
            preflight = {'case_id':'C02','runtime_fingerprint':fp,'corpus_id':prior['corpus']['id'],
                'corpus_sha256':sha(CORPUS),'input_sha256':locked,'as_of':case_data['as_of'],
                'required_context':required_checks(payload,expected),'initial_reservation':initial.entries[0]['reservation'],
                'hard_token_cap':25000,'max_network_requests':6,'max_seconds':90,'active_cooldowns':cooldowns,
                'historical_provider_headers':latest_headers,'historical_headers_are_not_live_quota':True,
                'provider_live_remaining_RPM_TPM_TPD':'UNKNOWN_NO_SEPARATE_QUOTA_QUERY',
                'billing_basis':'User explicitly confirmed configured Groq account is Free/no billing on 2026-10-21',
                'policy':'One independent allocation authorized by current request. Stop on HTTP429; no extra judge/tuning/retry attempt.',
                'phase3a_ledger_reset':False,'external_requests_during_preflight':0}
            save(Path('preflight.json'),preflight)
            if not live:
                print(json.dumps({'status':'PREFLIGHT_PASS','initial_reservation':initial.entries[0]['reservation'],'network_requests':0}))
                return
            assert not cooldowns and settings.groq_api_key.get_secret_value()
            ledger = RequestBudget(max_tokens=25000,max_requests=6,path=OUT/'request-budget.json',identity=fp)
            ctx = {'state':{},'wire_requests':0,'responses':[]}
            def unchanged():
                assert configuration_fingerprint(settings)==fp
                assert all(sha(ROOT/p)==value for p,value in locked.items())
                assert store.source_gate_status(store.release(None,True))['policy_sha256']==prior['source_policy']['canonical_sha256']
            class Transport(httpx.AsyncBaseTransport):
                def __init__(self):
                    self.real=httpx.AsyncHTTPTransport(retries=0)
                async def aclose(self):
                    await self.real.aclose()
                async def handle_async_request(self,request):
                    unchanged()
                    assert request.method=='POST' and str(request.url)=='https://api.groq.com/openai/v1/chat/completions'
                    body=json.loads(request.content); data=json.loads(body['messages'][-1]['content'])
                    schema=body['response_format']['json_schema']['name']
                    assert body['model']=='openai/gpt-oss-120b' and body['temperature']==0 and body['max_completion_tokens']==2048
                    assert data['question']==case['question'] and not data.get('history')
                    assert not any(s and len(s)>=12 and s in request.content.decode() for s in secrets)
                    assert not any(k in data for k in ('expected_answer','fixture_claims','gold_answers','releases'))
                    assert len(data.get('evidence',[]))<=16
                    state=ctx['state']; snapshot=copy.deepcopy(state.get('synthesis_sources',{}))
                    checks=required_checks(data,expected) if schema=='Draft' else []
                    if schema=='Draft':
                        assert all(r['present'] for r in checks)
                        assert len(json.dumps([data['evidence'],data['documents']],ensure_ascii=False,separators=(',',':')))<=7000
                        assert len(snapshot)==len(data['evidence']) and all(e['text']==s['text'] for e,s in zip(data['evidence'],snapshot.values()))
                    ctx['wire_requests']+=1
                    assert ctx['wire_requests']<=6
                    name=Path('wire')/f"{ctx['wire_requests']:02d}"
                    save(name/'request.json',body)
                    save(name/'sources.json',{'schema':schema,'required_context_checks':checks,
                        'retrieval_diagnostics':state.get('retrieval_diagnostics',{}),
                        'admitted':sorted(state.get('admitted_source_ids',[])), 'synthesis_snapshot':snapshot,
                        'retained':[{'id':e.chunk.id,'document_id':e.document.id,'locator':e.chunk.locator,'checksum':e.chunk.checksum} for e in state.get('evidence',[])],
                        'reservation':ledger.entries[-1]['reservation']})
                    started=time.monotonic()
                    try:
                        response=await self.real.handle_async_request(request)
                        await response.aread()
                    except BaseException as error:
                        save(name/'response.json',{'exception_type':type(error).__name__,
                            'latency_ms':round((time.monotonic()-started)*1000),'usage':'UNKNOWN_RESERVATION_RETAINED'})
                        raise
                    try:
                        raw_response=response.json()
                    except ValueError:
                        raw_response={}
                    if not isinstance(raw_response,dict):
                        raw_response={}
                    visible={k:raw_response[k] for k in ('id','object','created','model','usage','system_fingerprint') if k in raw_response}
                    visible['choices']=[{'finish_reason':c.get('finish_reason'),'message':{k:c.get('message',{}).get(k) for k in ('role','content')}} for c in raw_response.get('choices',[])]
                    if 'error' in raw_response:
                        visible['error']={k:raw_response['error'].get(k) for k in ('type','code','message')}
                    encoded=json.dumps(visible,ensure_ascii=False)
                    for secret in secrets:
                        if secret and len(secret)>=12:
                            encoded=encoded.replace(secret,'[REDACTED]')
                    headers={k:v for k,v in response.headers.items() if k.startswith('x-ratelimit-') or k=='retry-after'}
                    record={'schema':schema,'http_status':response.status_code,'body':json.loads(encoded),
                        'usage':raw_response.get('usage',{}),'headers':headers,'latency_ms':round((time.monotonic()-started)*1000),
                        'raw_response_sha256':hashlib.sha256(response.content).hexdigest(),'hidden_reasoning_not_saved':True}
                    save(name/'response.json',record);ctx['responses'].append(record)
                    if response.status_code==429:
                        ledger.settle(len(ledger.entries)-1,raw_response.get('usage',{}),status_code=429,headers=headers)
                        try:
                            delay=max(1,math.ceil(float(headers.get('retry-after','60'))))
                        except (ValueError,TypeError):
                            delay=60
                        store.set_cooldown(min(86400,delay));ctx['stop_reason']='provider_quota_stop_429'
                        raise ProviderUnavailable('Controlled pilot stops on provider quota exhaustion',retryable=False)
                    return response
            transport=Transport()
            provider=GroqProvider(settings,store,client=httpx.AsyncClient(transport=transport,timeout=25),usage_scope='operator',request_budget=ledger)
            capture={};events=[]
            class Observed(Agent):
                async def synthesize(self,state):
                    ctx['state']=state
                    return await super().synthesize(state)
                async def verify(self,state):
                    ctx['state']=state
                    value=await super().verify(state)
                    capture.setdefault('verifications',[]).append({'draft':value['draft'].model_dump(mode='json'),'verdict':value['verification'].model_dump(mode='json')})
                    return value
                async def finish(self,state):
                    value=await super().finish(state)
                    capture.update(final_draft=value['draft'].model_dump(mode='json'),final_verdict=value['verification'].model_dump(mode='json'),
                        final_synthesis_snapshot=copy.deepcopy(value.get('synthesis_sources',{})))
                    return value
            async def emit(event):
                events.append(event.model_dump(mode='json'))
            with (OUT/'LIVE_STARTED.json').open('x') as file:
                json.dump({'started_at':datetime.now(UTC).isoformat(),'case':'C02','attempt':1,'independent_allocation_tokens':25000},file)
            started=time.monotonic();record={'case_id':'C02','attempt':1,'runtime_fingerprint':fp,'as_of':case_data['as_of']}
            try:
                async with asyncio.timeout(90):
                    answer=await Observed(store,provider).run(ChatRequest(session_id='0'*36,message=case['question'],as_of=date.fromisoformat(case_data['as_of'])),emit)
                record['answer']=answer.model_dump(mode='json')
                record['operational_status']='INCOMPLETE' if answer.status in {'limited','error'} else 'COMPLETE'
                record['result_review']='PENDING_CONTENT_REVIEW' if answer.status=='answered' else 'FAIL_FALSE_ABSTENTION' if answer.status=='insufficient_evidence' else 'INCOMPLETE'
            except Exception as exc:
                record.update(operational_status='INCOMPLETE',result_review='INCOMPLETE',error_type=type(exc).__name__)
            finally:
                await provider.close()
            record.update(capture,events=events,elapsed_ms=round((time.monotonic()-started)*1000),
                wire_requests=ctx['wire_requests'],budget=ledger.summary(),stop_reason=ctx.get('stop_reason'),
                runtime_unchanged=configuration_fingerprint(settings)==fp,
                production_database_touched=False,phase3a_artifacts_modified=False)
            save(Path('attempt.json'),record)
            save(Path('operator-cooldown.json'),{'not_before':(datetime.now(UTC)+timedelta(seconds=store.cooldown())).isoformat(),'source':'Controlled C02 observed Groq cooldown'})
            unchanged()
            print(json.dumps({k:record[k] for k in ('operational_status','result_review','wire_requests','elapsed_ms','budget')}))
        finally:
            store.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    asyncio.run(run(args.live))
