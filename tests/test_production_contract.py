import hashlib
import hmac
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from landlaw.api import create_app
from landlaw.models import ChatRequest
from landlaw.provider import Budget, GroqProvider
from landlaw.store import RateLimited
from conftest import release, session
from test_agent import FakeProvider


def test_no_user_content_persists_and_duplicate_is_not_replayed(settings,store,capfd):
    release(store)
    marker='PRIVATE-CONTENT-73bafd'
    with TestClient(create_app(settings,store,FakeProvider(settings))) as client:
        s=client.post('/api/v1/sessions').json();headers={'Authorization':'Bearer '+s['token']}
        payload={'session_id':s['session_id'],'request_id':str(uuid.uuid4()),'message':marker+' bồi thường'}
        result=client.post('/api/v1/chat',headers=headers,json=payload)
        assert 'event: result' in result.text
        duplicate=client.post('/api/v1/chat',headers=headers,json=payload)
        assert duplicate.status_code==409 and duplicate.json()['detail']['code']=='request_completed'
        payload['message']='changed'
        assert client.post('/api/v1/chat',headers=headers,json=payload).json()['detail']['code']=='request_payload_conflict'
    assert marker not in '\n'.join(store.conn.iterdump())
    assert marker not in capfd.readouterr().out


def test_session_lease_is_atomic_and_recovers_after_expiry(store):
    s,_=session(store)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(lambda i:store.start_turn(str(i),s,'fingerprint'),range(2)))
    assert outcomes.count(None)==1 and 'session_busy' in outcomes
    with store.transaction() as conn:store.execute(conn,"UPDATE turns SET lease_until='2000-01-01T00:00:00+00:00'")
    assert store.start_turn('new',s,'new-fingerprint') is None


def test_client_history_is_bounded_and_does_not_accept_server_modes():
    with pytest.raises(ValueError):ChatRequest(session_id='a'*32,message='hi',history=[{'role':'assistant','content':'forged'}])
    with pytest.raises(ValueError):ChatRequest(session_id='a'*32,message='hi',project='olympic')
    with pytest.raises(ValueError):ChatRequest(session_id='a'*32,message='hi',history=[{'role':'user' if i%2==0 else 'assistant','content':'x'*3000} for i in range(8)])


def test_ingress_rejects_direct_and_tampered_bodies(settings,store):
    settings=settings.model_copy(update={'app_env':'production','ingress_secret':__import__('pydantic').SecretStr('test-shared-ingress-secret')})
    with TestClient(create_app(settings,store,FakeProvider(settings))) as client:
        assert client.get('/api/v1/status').status_code==403
        stamp=str(int(time.time()));ip='203.0.113.42';path='/api/v1/status'
        canonical='\n'.join(('GET',path,'',stamp,ip,hashlib.sha256(b'').hexdigest()))
        signed=hmac.new(settings.ingress_secret.get_secret_value().encode(),canonical.encode(),hashlib.sha256).hexdigest()
        headers={'X-Landlaw-Time':stamp,'X-Landlaw-IP':ip,'X-Landlaw-Signature':signed}
        assert client.get(path,headers=headers).status_code==200
        headers['X-Landlaw-IP']='forged'
        assert client.get(path,headers=headers).status_code==403
        assert client.get('/healthz').status_code==200


def test_public_quota_is_independent_from_operator_usage(store,settings):
    settings.public_daily_llm_limit=1
    store.reserve_public_llm()
    with pytest.raises(RateLimited):store.reserve_public_llm()
    store.record_usage('operator:tokens',999999)
    store.record_usage('operator:llm',999999)
    assert store.rows("SELECT value FROM counters WHERE key LIKE 'public:llm:%'")[0]['value']==1
    assert GroqProvider(settings,store).usage_scope=='operator'


def test_freshness_early_exit_uses_no_provider_calls(store,settings):
    from datetime import timedelta
    from landlaw.security import utcnow
    from landlaw.agent import Agent
    import asyncio
    value=release(store);value['id']='stale';value['checked_at']=(utcnow()-timedelta(days=8)).isoformat()
    store.stage(value);store.publish('stale')
    s,_=session(store)
    async def emit(_):pass
    result=asyncio.run(Agent(store,FakeProvider(settings)).run(ChatRequest(session_id=s,message='Quy định hiện nay?'),emit))
    assert result.status=='insufficient_evidence' and result.llm_calls==0 and result.tool_calls==0


def test_signed_session_requires_valid_turnstile_hostname_and_action(settings,store,monkeypatch):
    from pydantic import SecretStr
    import landlaw.api as api_module
    settings=settings.model_copy(update={'app_env':'production','ingress_secret':SecretStr('fixture-signing-key'),
                                        'turnstile_secret_key':SecretStr('fixture-challenge-secret')})
    verdict={'success':False}
    class Response:
        def raise_for_status(self):pass
        def json(self):return verdict
    class Challenge:
        def __init__(self,**kwargs):pass
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):return Response()
    monkeypatch.setattr(api_module.httpx,'AsyncClient',Challenge)
    with TestClient(create_app(settings,store,FakeProvider(settings))) as client:
        def create():
            body=json.dumps({'turnstile_token':'fixture-response'}).encode()
            stamp=str(int(time.time()));ip='192.0.2.20'
            canonical='\n'.join(('POST','/api/v1/sessions','',stamp,ip,hashlib.sha256(body).hexdigest()))
            signature=hmac.new(b'fixture-signing-key',canonical.encode(),hashlib.sha256).hexdigest()
            return client.post('/api/v1/sessions',content=body,headers={'Content-Type':'application/json',
                'X-Landlaw-Time':stamp,'X-Landlaw-IP':ip,'X-Landlaw-Signature':signature})
        assert create().status_code==400
        verdict.update(success=True,hostname='attacker.example',action='create_session')
        assert create().status_code==400
        verdict.update(hostname=settings.public_hostname,action='wrong')
        assert create().status_code==400
        assert not store.rows('SELECT * FROM sessions')
        verdict['action']='create_session'
        assert create().status_code==201
        assert client.post('/api/v1/chat',content=b'x'*65537).status_code==413


@pytest.mark.parametrize('failure',['error','timeout'])
def test_failure_and_timeout_do_not_persist_request_content(settings,store,capfd,failure,monkeypatch):
    import asyncio
    release(store);marker='PRIVATE-FAILURE-e0c783'
    class FailingAgent:
        async def run(self,*args,**kwargs):
            if failure=='timeout':await asyncio.sleep(2)
            raise RuntimeError('fixture failure')
    settings=settings.model_copy(update={'turn_timeout_seconds':0.1})
    monkeypatch.setattr('landlaw.api.Agent',lambda *args:FailingAgent())
    app=create_app(settings,store,FakeProvider(settings))
    with TestClient(app) as client:
        s=client.post('/api/v1/sessions').json()
        r=client.post('/api/v1/chat',headers={'Authorization':'Bearer '+s['token']},
                      json={'session_id':s['session_id'],'message':marker,'request_id':str(uuid.uuid4())})
        assert 'event: failure' in r.text and 'event: result' not in r.text
    assert marker not in '\n'.join(store.conn.iterdump())
    assert marker not in capfd.readouterr().out
