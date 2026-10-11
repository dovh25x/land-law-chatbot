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


async def test_quota_returns_retry_and_never_exposes_provider_body(settings, store):
    def handler(request):
        return httpx.Response(429, headers={'Retry-After': '37'}, json={'error': {'message': 'secret test-key'}})
    provider = Gemini(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(RateLimited) as error:
        await provider.generate(Probe, 'probe', {}, Budget())
    assert error.value.retry_after == 37
    await provider.close()


async def test_error_body_and_malformed_schema_are_blocked(settings, store):
    responses = [httpx.Response(500, json={'error': {'message': 'test-key private prompt'}}), httpx.Response(200, json={'candidates': [{'content': {'parts': [{'text': 'not JSON'}]}}]})]
    provider = Gemini(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(lambda _: responses.pop(0))))
    for _ in range(2):
        with pytest.raises(ProviderUnavailable) as error:
            await provider.generate(Probe, 'probe', {}, Budget())
        assert 'test-key' not in str(error.value) and 'private prompt' not in str(error.value)
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
