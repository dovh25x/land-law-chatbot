"""Operator quota evidence must survive suite boundaries without hook accumulation."""
from datetime import date
from types import SimpleNamespace

import httpx


async def test_capacity_reset_survives_next_suite_and_restores_provider(store,settings,monkeypatch,tmp_path):
    import landlaw.evaluation as evaluation
    from conftest import release
    from landlaw.models import ChatResult
    release(store)
    settings=settings.model_copy(update={'reports_dir':tmp_path/'reports'})
    monkeypatch.setattr(evaluation,'frozen_dataset',lambda *_:([{'id':'SAFE','question':'Fixture capacity check','as_of':'2024-08-02','rubric':[]}],'fixture-suite'))
    monkeypatch.setattr(evaluation,'validate_suite_corpus',lambda *_:None)
    sleeps=[]
    async def sleep(seconds):sleeps.append(seconds)
    monkeypatch.setattr(evaluation.asyncio,'sleep',sleep)
    async def generate(*_):raise AssertionError('No LLM fixture request')
    client=httpx.AsyncClient(transport=httpx.MockTransport(lambda request:httpx.Response(200,headers={
        'x-ratelimit-remaining-tokens':'1','x-ratelimit-limit-tokens':'8000','x-ratelimit-reset-tokens':'15s'})))
    provider=SimpleNamespace(settings=settings,configured=True,client=client,generate=generate)
    class FixtureAgent:
        def __init__(self,*_):pass
        async def run(self,request,emit,release_id):
            await client.get('https://api.groq.com/fixture-capacity')
            return ChatResult(status='insufficient_evidence',content='Fixture only',as_of=date(2024,8,2),
                trace_id='fixture',model=settings.generation_model,embedding_model=settings.embedding_model,
                mode='agentic',corpus_release=release_id)
    monkeypatch.setattr(evaluation,'Agent',FixtureAgent)
    try:
        await evaluation.evaluate(settings,store,provider,'smoke')
        assert store.cooldown()>=14
        assert provider.generate is generate and client.event_hooks['response']==[]
        await evaluation.evaluate(settings,store,provider,'supplemental')
        assert sleeps and sleeps[0]>=13
        assert provider.generate is generate and client.event_hooks['response']==[]
    finally:await client.aclose()
