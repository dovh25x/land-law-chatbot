import json

import httpx
import pytest
from pydantic import BaseModel

from landlaw.agent import Plan, Verification
from landlaw.models import Draft
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


async def test_groq_answer_has_only_citable_claims_and_no_unused_summary_field(settings,store):
    def respond(request):
        shape=json.loads(request.content)['response_format']['json_schema']['schema']
        assert 'summary' not in shape['properties']
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({
            'status':'answered','claims':[{'kind':'legal_rule','text':'Điều kiện có trong nguồn.',
                'citation_ids':['C1']}],'missing_facts':[],'next_steps':[],'out_of_scope':False})}}]})
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.gemini_api_key})
    provider=Gemini(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    try:
        draft=await provider.generate(Draft,'Answer in claims',{},Budget())
        assert draft.summary=='' and draft.claims[0].citation_ids==['C1']
    finally:await provider.close()


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
        assert seen[0]['tool_choice']=='none'
        assert 'plain data for a separate application' in seen[0]['messages'][0]['content']
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


async def test_rejected_provider_tool_attempt_retries_only_as_json_and_never_executes(settings,store,monkeypatch):
    import asyncio
    class Probe(BaseModel):ok: bool
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.gemini_api_key})
    attempts=[]
    def respond(request):
        body=json.loads(request.content);attempts.append(body)
        assert body['tool_choice']=='none' and 'tools' not in body
        if len(attempts)==1:
            return httpx.Response(400,json={'error':{'code':'tool_use_failed','message':'private generated tool attempt'}})
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"ok":true}'}}],'usage':{'total_tokens':12}})
    async def no_wait(_):pass
    monkeypatch.setattr(asyncio,'sleep',no_wait)
    provider=Gemini(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)));budget=Budget()
    try:
        assert (await provider.generate(Probe,'Return JSON',{},budget)).ok
        assert budget.llm_calls==2 and len(attempts)==2
    finally:await provider.close()


async def test_planner_lookups_are_json_data_and_map_back_to_read_only_actions(settings,store):
    def respond(request):
        body=json.loads(request.content);shape=body['response_format']['json_schema']['schema']
        assert 'lookups' in shape['properties'] and 'tools' not in shape['properties']
        assert 'tools' not in body and body['tool_choice']=='none'
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({
            'lookups':[{'name':'open_article','query':'Điều 5','document_id':'nd-151-2025','locator':'Điều 5'}],
            'missing_facts':[],'out_of_scope':False})}}]})
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.gemini_api_key})
    provider=Gemini(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    try:
        result=await provider.generate(Plan,'Return lookup descriptors',{},Budget())
        assert result.tools[0].name=='open_article' and result.tools[0].document_id=='nd-151-2025'
    finally:await provider.close()


@pytest.mark.parametrize('groq_available', [True, False])
async def test_groq_selection_never_uses_a_retained_nvidia_key(settings, store, groq_available):
    from pydantic import SecretStr
    from landlaw.provider import ProviderUnavailable
    class Probe(BaseModel):
        ok: bool
    requests = []
    def respond(request):
        requests.append(request)
        assert request.url.host == 'api.groq.com'
        assert request.headers['authorization'] == 'Bearer groq-test-placeholder'
        return httpx.Response(200, json={'choices':[{'message':{'content':'{"ok":true}'}}]})
    config = settings.model_copy(update={'llm_provider':'groq', 'groq_model':'openai/gpt-oss-20b',
        'groq_api_key':SecretStr('groq-test-placeholder' if groq_available else ''),
        'nvidia_api_key':SecretStr('nvidia-unused-test-placeholder')})
    provider = Gemini(config, store, httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    try:
        assert provider.configured is groq_available
        if groq_available:
            assert (await provider.generate(Probe, 'Return JSON', {}, Budget())).ok
            assert len(requests) == 1
        else:
            with pytest.raises(ProviderUnavailable, match='GROQ_API_KEY'):
                await provider.generate(Probe, 'Return JSON', {}, Budget())
            assert requests == []
    finally:
        await provider.close()
