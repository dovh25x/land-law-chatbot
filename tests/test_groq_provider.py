import json

import httpx
import pytest
from pydantic import BaseModel

from landlaw.agent import Plan, Verification
from landlaw.models import Draft
from landlaw.provider import Budget, GroqProvider, strict_generation_schema
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
        payload=json.loads(request.content)
        assert payload['reasoning_effort']=='medium' and payload['max_completion_tokens']==2048
        shape=payload['response_format']['json_schema']['schema']
        assert 'summary' not in shape['properties']
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({
            'status':'answered','claims':[{'kind':'legal_rule','text':'Điều kiện có trong nguồn.',
                'citation_ids':['C1']}],'missing_facts':[],'next_steps':[],'out_of_scope':False})}}]})
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.groq_api_key})
    provider=GroqProvider(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
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
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.groq_api_key})
    provider=GroqProvider(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    budget=Budget()
    try:
        assert (await provider.generate(Probe,'Return JSON',{},budget)).ok
        assert 'tools' not in seen[0]
        assert seen[0]['tool_choice']=='none'
        assert seen[0]['reasoning_effort']=='low' and seen[0]['max_completion_tokens']==2048
        assert 'plain data for a separate application' in seen[0]['messages'][0]['content']
        assert seen[0]['response_format']['json_schema']['strict']
        assert budget.llm_calls==1 and budget.tokens==17
        assert config.generation_model=='openai/gpt-oss-120b'
    finally:await provider.close()


async def test_groq_tool_step_uses_native_tools_without_structured_output(settings,store):
    seen=[]
    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200,json={'choices':[{'message':{
            'content':'',
            'tool_calls':[{'id':'call-1','type':'function','function':{
                'name':'search_legal_evidence','arguments':'{"query":"điều kiện bồi thường"}'}}]},
            'finish_reason':'tool_calls'}],'usage':{'total_tokens':21}})
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.groq_api_key})
    provider=GroqProvider(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    budget=Budget()
    try:
        result=await provider.tool_step(
            'Choose a tool',[{'role':'user','content':'Tôi có được bồi thường không?'}],
            [{'type':'function','function':{'name':'search_legal_evidence','parameters':{'type':'object'}}}],budget)
        assert result['tool_calls'][0]['name']=='search_legal_evidence'
        assert 'tools' in seen[0] and seen[0]['tool_choice']=='auto'
        assert 'response_format' not in seen[0]
        assert budget.llm_calls==1 and budget.tokens==21
    finally:await provider.close()


async def test_groq_tool_step_format_failure_is_not_retried(settings,store):
    from landlaw.provider import ProviderUnavailable
    attempts=[]
    def respond(request):
        attempts.append(json.loads(request.content))
        return httpx.Response(400,json={'error':{'code':'tool_use_failed','message':'private output'}})
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.groq_api_key})
    provider=GroqProvider(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    try:
        with pytest.raises(ProviderUnavailable):
            await provider.tool_step('Choose a tool',[{'role':'user','content':'x'}],[{'type':'function','function':{'name':'x'}}],Budget())
        assert len(attempts)==1
    finally:await provider.close()


async def test_groq_daily_quota_stops_without_retry_loop(settings,store):
    class Probe(BaseModel):ok: bool
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.groq_api_key})
    provider=GroqProvider(config,store,httpx.AsyncClient(transport=httpx.MockTransport(
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
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.groq_api_key})
    attempts=[]
    def respond(request):
        body=json.loads(request.content);attempts.append(body)
        assert body['tool_choice']=='none' and 'tools' not in body
        if len(attempts)==1:
            return httpx.Response(400,json={'error':{'code':'tool_use_failed','message':'private generated tool attempt'}})
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"ok":true}'}}],'usage':{'total_tokens':12}})
    async def no_wait(_):pass
    monkeypatch.setattr(asyncio,'sleep',no_wait)
    provider=GroqProvider(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)));budget=Budget()
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
    config=settings.model_copy(update={'llm_provider':'groq','groq_api_key':settings.groq_api_key})
    provider=GroqProvider(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    try:
        result=await provider.generate(Plan,'Return lookup descriptors',{},Budget())
        assert result.tools[0].name=='open_article' and result.tools[0].document_id=='nd-151-2025'
    finally:await provider.close()


@pytest.mark.parametrize('groq_available', [True, False])
async def test_groq_requires_its_own_key(settings, store, groq_available):
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
        'groq_api_key':SecretStr('groq-test-placeholder' if groq_available else '')})
    provider = GroqProvider(config, store, httpx.AsyncClient(transport=httpx.MockTransport(respond)))
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
