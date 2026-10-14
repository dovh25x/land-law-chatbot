import json

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from landlaw.agent import Plan
from landlaw.models import Draft
from landlaw.provider import Budget, Gemini, ProviderUnavailable
from landlaw.store import RateLimited


class Probe(BaseModel):
    ok: bool


def configuration(settings):
    return settings.model_copy(update={'llm_provider':'nvidia','nvidia_api_key':SecretStr('nvidia-test-only')})


async def test_nvidia_selection_keeps_embedding_contract_and_never_calls_other_providers(settings,store):
    config=configuration(settings)
    def respond(request):
        assert str(request.url)=='https://integrate.api.nvidia.com/v1/chat/completions'
        assert request.headers['Authorization']=='Bearer nvidia-test-only'
        body=json.loads(request.content)
        assert body['model']=='nvidia/nemotron-3-super-120b-a12b'
        assert body['stream'] is False and body['reasoning_effort']=='none'
        assert 'tools' not in body and 'tool_choice' not in body
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"ok":true}','reasoning_content':'private reasoning'}}],
            'usage':{'total_tokens':21}})
    provider=Gemini(config,store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    try:
        budget=Budget();result=await provider.generate(Probe,'Return JSON',{},budget)
        assert result.ok and budget.tokens==21 and budget.llm_calls==1
        assert config.generation_model==config.nvidia_model
        assert config.embedding_model==settings.embedding_model and config.embedding_dimensions==settings.embedding_dimensions
    finally:await provider.close()


async def test_missing_nvidia_key_does_not_use_present_gemini_key(settings,store):
    config=configuration(settings).model_copy(update={'nvidia_api_key':SecretStr('')})
    def forbidden(_):raise AssertionError('No provider may be contacted without selected key')
    provider=Gemini(config,store,httpx.AsyncClient(transport=httpx.MockTransport(forbidden)))
    try:
        assert not provider.configured
        with pytest.raises(ProviderUnavailable,match='NVIDIA_API_KEY'):
            await provider.generate(Probe,'Return JSON',{},Budget())
    finally:await provider.close()


async def test_nvidia_json_lookups_map_to_bounded_application_tools(settings,store):
    def respond(request):
        body=json.loads(request.content)
        assert '"lookups"' in body['messages'][0]['content']
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({
            'lookups':[{'name':'open_article','document_id':'known-law','locator':'Điều 2','query':''}],
            'missing_facts':[],'out_of_scope':False})}}]})
    provider=Gemini(configuration(settings),store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    try:
        result=await provider.generate(Plan,'Select read tools',{},Budget())
        assert result.tools[0].name=='open_article' and result.tools[0].document_id=='known-law'
    finally:await provider.close()


async def test_nvidia_invalid_json_retry_counts_calls_and_uses_local_validation(settings,store):
    attempts=[]
    def respond(request):
        attempts.append(request)
        content='{"ok":"invalid-boolean"}' if len(attempts)==1 else '{"ok":true}'
        return httpx.Response(200,json={'choices':[{'message':{'content':content}}],'usage':{'total_tokens':4}})
    provider=Gemini(configuration(settings),store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    try:
        budget=Budget();assert (await provider.generate(Probe,'Return JSON',{},budget)).ok
        assert budget.llm_calls==2 and budget.tokens==8
    finally:await provider.close()


@pytest.mark.parametrize('status',[401,403,422,202])
async def test_nvidia_auth_validation_or_pending_errors_are_sanitized_without_fallback(settings,store,status):
    provider=Gemini(configuration(settings),store,httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _:httpx.Response(status,json={'error':'private key/prompt must never be shown'}))))
    try:
        with pytest.raises(ProviderUnavailable) as error:
            await provider.generate(Probe,'Return JSON',{},Budget())
        assert 'private' not in str(error.value) and 'nvidia-test-only' not in str(error.value)
    finally:await provider.close()


async def test_nvidia_quota_preserves_retry_after_and_stops_long_retries(settings,store):
    provider=Gemini(configuration(settings),store,httpx.AsyncClient(transport=httpx.MockTransport(
        lambda _:httpx.Response(429,headers={'Retry-After':'3600.1'},json={'error':'private quota body'}))))
    try:
        budget=Budget()
        with pytest.raises(RateLimited) as error:await provider.generate(Probe,'Return JSON',{},budget)
        assert error.value.retry_after==3601 and error.value.source=='provider' and budget.llm_calls==1
    finally:await provider.close()


async def test_nvidia_draft_schema_only_exposes_citable_claims(settings,store):
    def respond(request):
        instruction=json.loads(request.content)['messages'][0]['content']
        assert '"summary"' not in instruction
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({
            'status':'answered','claims':[{'text':'Quy định có điều kiện trong nguồn.','kind':'legal_rule','citation_ids':['C1']}],
            'missing_facts':[],'next_steps':[],'out_of_scope':False})}}]})
    provider=Gemini(configuration(settings),store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    try:
        draft=await provider.generate(Draft,'Answer using cited claims',{},Budget())
        assert draft.summary=='' and draft.claims[0].citation_ids==['C1']
    finally:await provider.close()


async def test_nvidia_graph_blocks_invalid_citation_even_when_model_verifier_approves(settings,store):
    from conftest import document,release,session
    from landlaw.agent import Agent
    from landlaw.models import ChatRequest
    law=document(document_number='40/2026/QĐ-UBND')
    release(store,[law]);sid,_=session(store)
    def respond(request):
        body=json.loads(request.content)
        assert request.url.host=='integrate.api.nvidia.com'
        if '"supported_claim_indexes"' in body['messages'][0]['content']:
            content={'supported_claim_indexes':[0],'supporting_spans':[],
                'issues':[],'needs_more_evidence':False,'followup_query':''}
        else:
            content={'status':'answered','claims':[{'text':'Mỗi hộ chắc chắn nhận 50 tỷ đồng.',
                'kind':'legal_rule','citation_ids':['invented-citation']}],
                'missing_facts':[],'next_steps':[],'out_of_scope':False}
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(content)}}]})
    provider=Gemini(configuration(settings),store,httpx.AsyncClient(transport=httpx.MockTransport(respond)))
    async def emit(_):pass
    try:
        answer=await Agent(store,provider).run(ChatRequest(session_id=sid,
            message='Điều 1 Quyết định 40/2026/QĐ-UBND quy định điều kiện gì?',mode='agentic'),emit)
        assert answer.status=='insufficient_evidence'
        assert not answer.citations and not answer.verified_claims and '50 tỷ' not in answer.content
        assert answer.model==configuration(settings).nvidia_model and answer.llm_calls<=6
    finally:await provider.close()
