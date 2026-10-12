import json
import math

import httpx
import pytest
from pydantic import BaseModel

from landlaw.provider import Budget, BudgetExceeded, Gemini, ProviderUnavailable
from landlaw.store import RateLimited


class Probe(BaseModel):
    ok: bool


async def test_structured_rest_uses_secret_header_and_counts_usage(settings, store):
    def handler(request):
        assert 'test-key' not in str(request.url)
        assert request.headers['x-goog-api-key'] == 'test-key'
        body = json.loads(request.content)
        assert body['generationConfig']['responseJsonSchema']['properties']['ok']['type'] == 'boolean'
        return httpx.Response(200, json={'candidates': [{'content': {'parts': [{'thought': True, 'text': 'private'}, {'text': '{"ok":true}'}]}}], 'usageMetadata': {'totalTokenCount': 17}})
    provider = Gemini(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    budget = Budget()
    assert (await provider.generate(Probe, 'probe', {}, budget)).ok
    assert budget.llm_calls == 1 and budget.tokens == 17
    await provider.close()


async def test_batch_creates_separate_normalized_vectors(settings, store):
    def handler(request):
        body = json.loads(request.content)
        assert request.url.path.endswith(':batchEmbedContents')
        assert len(body['requests']) == 2
        assert all(len(r['content']['parts']) == 1 and r['outputDimensionality'] == 768 for r in body['requests'])
        return httpx.Response(200, json={'embeddings': [{'values': [1.0]+[0.0]*767}, {'values': [0.0, 2.0]+[0.0]*766}]})
    provider = Gemini(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    vectors = await provider.embed_many(['a', 'b'])
    assert vectors[0] != vectors[1]
    assert all(math.isclose(sum(v*v for v in vector), 1) for vector in vectors)
    await provider.close()


async def test_quota_returns_retry_and_never_exposes_provider_body(settings, store, monkeypatch):
    async def no_sleep(_): pass
    monkeypatch.setattr('landlaw.provider.asyncio.sleep',no_sleep)
    def handler(request):
        return httpx.Response(429, headers={'Retry-After': '37'}, json={'error': {'message': 'secret test-key'}})
    provider = Gemini(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    budget=Budget()
    with pytest.raises(RateLimited) as error:
        await provider.generate(Probe, 'probe', {}, budget)
    assert error.value.retry_after == 37
    assert error.value.source=='provider' and budget.llm_calls==3
    await provider.close()


async def test_daily_quota_honours_google_retryinfo(settings, store):
    provider = Gemini(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(429, json={"error": {"details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "20927.1s"}]}}))))
    with pytest.raises(RateLimited) as error:
        await provider.embed("document")
    assert error.value.retry_after == 20928
    await provider.close()


async def test_error_body_and_malformed_schema_are_blocked(settings, store):
    malformed = httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': 'not JSON'}]}}]})
    responses = [httpx.Response(500, json={'error': {'message': 'test-key private prompt'}}) for _ in range(3)] + [malformed, malformed]
    provider = Gemini(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(lambda _: responses.pop(0))))
    for _ in range(2):
        with pytest.raises(ProviderUnavailable) as error:
            await provider.generate(Probe, 'probe', {}, Budget())
        assert 'test-key' not in str(error.value) and 'private prompt' not in str(error.value)
    await provider.close()


async def test_schema_repair_is_bounded_and_counted(settings, store):
    responses = [httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'wrong'}]}}]}), httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'{"ok":true}'}]}}]})]
    provider = Gemini(settings,store,httpx.AsyncClient(transport=httpx.MockTransport(lambda _:responses.pop(0))))
    budget = Budget()
    assert (await provider.generate(Probe,'probe',{},budget)).ok
    assert budget.llm_calls == 2
    await provider.close()


def test_llm_budget_and_bad_vectors():
    budget = Budget()
    for _ in range(6):
        budget.llm()
    with pytest.raises(BudgetExceeded):
        budget.llm()
    for vector in [[0.0]*768, [math.nan]*768, [1.0]*767]:
        with pytest.raises(ProviderUnavailable):
            Gemini.normalize_vector(vector)


async def test_workers_ai_generation_validates_schema_and_ignores_reasoning(settings, store):
    selected=settings.model_copy(update={'llm_provider':'cloudflare','cloudflare_account_id':'a'*32,
        'cloudflare_ai_api_token':settings.gemini_api_key})
    def handle(request):
        assert request.url.host=='api.cloudflare.com' and 'test-key' not in str(request.url)
        assert request.headers['authorization']=='Bearer test-key'
        body=json.loads(request.content)
        assert body['model']==selected.generation_model
        assert body['response_format']['json_schema']['properties']['ok']['type']=='boolean'
        assert body['response_format']['json_schema']['required']==['ok']
        return httpx.Response(200,json={'choices':[{'message':{'content':'{"ok":true}','reasoning_content':'private thoughts'}}],
            'usage':{'total_tokens':42,'neurons':1.25}})
    provider=Gemini(selected,store,httpx.AsyncClient(transport=httpx.MockTransport(handle)))
    budget=Budget()
    assert (await provider.generate(Probe,'probe',{},budget)).ok
    assert budget.tokens==42 and budget.llm_calls==1
    assert store.rows("SELECT value FROM counters WHERE key LIKE 'usage:workers-ai-millineurons:%'")[0]['value']==1250
    await provider.close()


async def test_workers_ai_quota_remains_provider_limit_and_is_sanitized(settings,store):
    selected=settings.model_copy(update={'llm_provider':'cloudflare','cloudflare_account_id':'a'*32,
        'cloudflare_ai_api_token':settings.gemini_api_key})
    provider=Gemini(selected,store,httpx.AsyncClient(transport=httpx.MockTransport(lambda _:
        httpx.Response(429,headers={'Retry-After':'7200'},json={'errors':[{'message':'test-key private prompt'}]}))))
    budget=Budget()
    with pytest.raises(RateLimited) as error: await provider.generate(Probe,'probe',{},budget)
    assert error.value.source=='provider' and error.value.retry_after==7200 and budget.llm_calls==1
    assert 'test-key' not in str(error.value)
    await provider.close()


def test_workers_ai_daily_allocation_and_capacity_have_distinct_waits():
    from landlaw.embedding import workers_ai_retry_after
    daily=httpx.Response(429,json={'errors':[{'code':3036,'message':'daily allocation'}]})
    busy=httpx.Response(429,json={'errors':[{'code':3040,'message':'capacity'}]})
    assert 1<=workers_ai_retry_after(daily)<=86400
    assert workers_ai_retry_after(busy)==60
    assert workers_ai_retry_after(httpx.Response(429,headers={'Retry-After':'37.5'}))==38
