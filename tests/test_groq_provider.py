import json

import httpx
import pytest
from pydantic import BaseModel

from landlaw.agent import Plan, Verification
from landlaw.provider import Budget, Gemini, strict_generation_schema
from landlaw.store import RateLimited


def test_strict_groq_schema_closes_nested_objects_and_uses_source_span_ids():
    shape=strict_generation_schema(Plan)
    assert shape['additionalProperties'] is False
    assert set(shape['required'])==set(shape['properties'])
    tool=shape['$defs']['ToolCall']
    assert tool['additionalProperties'] is False
    assert set(tool['required'])==set(tool['properties'])
    verify=strict_generation_schema(Verification)
    assert 'supporting_quotes' not in verify['properties']
    assert 'supporting_spans' in verify['properties']


async def test_groq_transport_has_no_remote_tools_and_does_not_expose_reasoning(settings,store):
    class Probe(BaseModel):ok: bool
    seen=[]
    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"ok":true}','reasoning':'private model reasoning'}}],
                                       'usage':{'total_tokens':17}})
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.gemini_api_key})
    provider=Gemini(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    budget=Budget()
    try:
        assert (await provider.generate(Probe,'Return JSON',{},budget)).ok
        assert 'tools' not in seen[0]
        assert seen[0]['response_format']['json_schema']['strict']
        assert budget.llm_calls==1 and budget.tokens==17
        assert config.generation_model=='openai/gpt-oss-120b'
    finally:await provider.close()


async def test_groq_daily_quota_stops_without_retry_loop(settings,store):
    class Probe(BaseModel):ok: bool
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.gemini_api_key})
    provider=Gemini(config,store,httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _:httpx.Response(429,headers={'Retry-After':'3600.1'},json={'error':{'message':'must never be logged'}}))))
    budget=Budget()
    try:
        with pytest.raises(RateLimited) as error:
            await provider.generate(Probe,'Return JSON',{},budget)
        assert error.value.source=='provider' and error.value.retry_after==3601
        assert budget.llm_calls==1
    finally:await provider.close()
