"""Offline transport and accounting regressions; no legal pilot case or API."""
import json

import httpx
import pytest
from landlaw.provider import Budget, BudgetExceeded, GroqProvider, ProviderUnavailable
from landlaw.request_budget import RequestBudget
from landlaw.store import RateLimited
from pydantic import BaseModel, Field


class Probe(BaseModel):
    ok: bool


def wire(maximum=2048, text='public synthetic input'):
    return {'messages': [{'role': 'user', 'content': text}], 'max_completion_tokens': maximum}


def test_request_specific_reservation_and_usage_fields():
    ledger = RequestBudget()
    ident = ledger.reserve(wire())
    before = ledger.summary()
    assert before['confirmed_usage'] == before['estimated_usage'] == 0
    assert before['reserved_budget'] == len(json.dumps(wire(), ensure_ascii=False, separators=(',', ':')).encode()) + 4096 + 2048
    ledger.settle(ident, {'total_tokens': 100}, status_code=200)
    assert ledger.summary()['confirmed_usage'] == 100
    assert ledger.summary()['remaining_test_budget'] == 59900
    assert ledger.summary()['reserved_budget'] == 0
    larger = RequestBudget()
    larger.reserve(wire(maximum=4096, text='public' * 100))
    assert larger.summary()['reserved_budget'] > before['reserved_budget']


@pytest.mark.parametrize('status', [200, 400, 429, 500, None])
def test_unknown_usage_is_not_freed_even_for_rejected_request(status):
    ledger = RequestBudget()
    ident = ledger.reserve(wire())
    reserved = ledger.summary()['reserved_budget']
    ledger.settle(ident, {}, status_code=status)
    assert ledger.summary()['confirmed_usage'] == ledger.summary()['reserved_budget'] == 0
    assert ledger.summary()['estimated_usage'] == reserved
    assert ledger.summary()['remaining_test_budget'] == 60000 - reserved


@pytest.mark.parametrize('reported', [-1, True, '4', None])
def test_invalid_usage_is_unknown_not_a_refund(reported):
    ledger = RequestBudget()
    ident = ledger.reserve(wire())
    ledger.settle(ident, {'total_tokens': reported})
    assert ledger.summary()['estimated_usage'] > 0
    assert ledger.summary()['confirmed_usage'] == 0


def test_crash_and_resume_keep_pending_reservation_and_limits(tmp_path):
    path = tmp_path / 'request-budget.json'
    original = RequestBudget(path=path, identity='locked')
    original.reserve(wire())
    resumed = RequestBudget(path=path, identity='locked')
    assert resumed.summary() == original.summary()
    assert resumed.summary()['reserved_budget'] > 0
    with pytest.raises(ValueError, match='identity/limits changed'):
        RequestBudget(path=path, identity='changed')


def test_zero_request_run_has_a_durable_resumable_ledger(tmp_path):
    path = tmp_path / 'request-budget.json'
    ledger = RequestBudget(path=path, identity='zero-request-run')
    assert path.is_file()
    assert RequestBudget(path=path, identity='zero-request-run').summary() == ledger.summary()
    assert ledger.summary()['requests_reserved'] == 0


def test_block_before_reserve_is_durable_and_does_not_spend(tmp_path):
    path = tmp_path / 'request-budget.json'
    ledger = RequestBudget(max_tokens=1, path=path)
    with pytest.raises(BudgetExceeded, match='test_token_cap'):
        ledger.reserve(wire())
    assert ledger.summary()['requests_reserved'] == 0
    assert ledger.summary()['remaining_test_budget'] == 1
    restored = RequestBudget(max_tokens=1, path=path)
    with pytest.raises(BudgetExceeded, match='test_token_cap'):
        restored.reserve(wire())


def test_total_request_cap_and_double_settlement():
    ledger = RequestBudget(max_requests=1)
    ident = ledger.reserve(wire())
    ledger.settle(ident, {'total_tokens': 0})
    with pytest.raises(ValueError, match='already settled'):
        ledger.settle(ident, {'total_tokens': 1})
    with pytest.raises(BudgetExceeded, match='test_request_cap'):
        ledger.reserve(wire())


def test_provider_reports_over_bound_blocks_future_requests():
    ledger = RequestBudget()
    ident = ledger.reserve(wire())
    upper = ledger.summary()['reserved_budget']
    with pytest.raises(BudgetExceeded, match='exceeded_reservation'):
        ledger.settle(ident, {'total_tokens': upper + 1})
    assert ledger.summary()['confirmed_usage'] == upper + 1
    with pytest.raises(BudgetExceeded):
        ledger.reserve(wire())


def test_provider_quota_headers_separate_from_accounting():
    ledger = RequestBudget()
    ident = ledger.reserve(wire())
    ledger.settle(ident, {}, status_code=429, headers={
        'retry-after': '4', 'x-ratelimit-limit-tokens': '8000',
        'x-ratelimit-remaining-tokens': '3746', 'x-ratelimit-reset-tokens': '31.904s',
        'authorization': 'Never persist', 'x-ratelimit-limit-requests': 'not numeric private message'})
    assert ledger.entries[0]['provider_rate_limits'] == {
        'retry-after': '4', 'x-ratelimit-limit-tokens': '8000',
        'x-ratelimit-remaining-tokens': '3746', 'x-ratelimit-reset-tokens': '31.904s'}
    assert ledger.summary()['remaining_test_budget'] > 3746


async def test_transport_is_not_called_when_test_budget_blocks(settings, store):
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(200)
    ledger = RequestBudget(max_tokens=1)
    provider = GroqProvider(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(respond)), request_budget=ledger)
    try:
        with pytest.raises(BudgetExceeded):
            await provider.generate(Probe, 'Return JSON', {}, Budget())
        assert requests == []
    finally:
        await provider.close()


async def test_success_refunds_only_confirmed_usage(settings, store):
    ledger = RequestBudget()
    provider = GroqProvider(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(
        200, json={'choices': [{'message': {'content': '{"ok":true}'}}], 'usage': {'total_tokens': 17}}))), request_budget=ledger)
    budget = Budget()
    try:
        assert (await provider.generate(Probe, 'Return JSON', {}, budget)).ok
        assert ledger.summary()['confirmed_usage'] == budget.tokens == 17
        assert ledger.summary()['reserved_budget'] == ledger.summary()['estimated_usage'] == 0
    finally:
        await provider.close()


async def test_429_retry_is_single_scheduled_retry_with_unknown_charge(settings, store, monkeypatch):
    requests, sleeps = [], []
    ledger = RequestBudget()
    def respond(request):
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(429, headers={'retry-after': '3.39'}, json={'error': {'code': 'rate_limit_exceeded'}})
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"ok":true}'}}], 'usage': {'total_tokens': 20}})
    async def wait(seconds):
        sleeps.append(seconds)
    monkeypatch.setattr('landlaw.provider.asyncio.sleep', wait)
    provider = GroqProvider(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(respond)), request_budget=ledger)
    budget = Budget()
    try:
        assert (await provider.generate(Probe, 'Return JSON', {}, budget)).ok
        assert sleeps == [4] and len(requests) == budget.llm_calls == 2
        assert requests[0] == requests[1]
        assert ledger.summary()['confirmed_usage'] == 20
        assert ledger.summary()['estimated_usage'] == ledger.entries[0]['reservation']
        assert store.cooldown() > 0  # A fake sleep never clears a real shared cooldown.
    finally:
        await provider.close()


async def test_long_cooldown_stops_after_one_request(settings, store):
    ledger = RequestBudget()
    provider = GroqProvider(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(
        429, headers={'retry-after': '3600'}, json={'error': {'code': 'rate_limit_exceeded'}}))), request_budget=ledger)
    try:
        with pytest.raises(RateLimited):
            await provider.generate(Probe, 'Return JSON', {}, Budget())
        assert len(ledger.entries) == 1 and ledger.summary()['estimated_usage'] > 0
    finally:
        await provider.close()


async def test_provider_format_failure_retries_with_feedback_and_same_strict_schema(settings, store, monkeypatch):
    requests = []
    ledger = RequestBudget()
    def respond(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            return httpx.Response(400, json={'error': {'code': 'json_validate_failed',
                'failed_generation': 'must never be accepted as an answer'}})
        return httpx.Response(200, json={'choices': [{'message': {'content': '{"ok":true}'}}], 'usage': {'total_tokens': 11}})
    async def wait(_):
        pass
    monkeypatch.setattr('landlaw.provider.asyncio.sleep', wait)
    provider = GroqProvider(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(respond)), request_budget=ledger)
    try:
        assert (await provider.generate(Probe, 'Return JSON', {}, Budget())).ok
        assert len(requests) == 2
        assert requests[0]['response_format'] == requests[1]['response_format']
        assert requests[1]['response_format']['json_schema']['strict'] is True
        correction = '\nLượt trước không khớp schema. Trả duy nhất JSON đúng responseJsonSchema; dùng đúng kiểu trường và giá trị enum, không có markdown.'
        assert requests[1]['messages'][0]['content'].replace(correction, '') == requests[0]['messages'][0]['content']
        assert ledger.summary()['estimated_usage'] > 0 and ledger.summary()['confirmed_usage'] == 11
    finally:
        await provider.close()


@pytest.mark.parametrize('kind', ['provider_error', 'outer_json', 'null_content', 'local_json', 'local_schema'])
async def test_format_failures_are_bounded_and_never_salvaged(settings, store, monkeypatch, kind):
    class Bounded(BaseModel):
        value: int = Field(ge=1, le=2)
    calls = []
    ledger = RequestBudget()
    def respond(request):
        calls.append(request)
        if kind == 'provider_error':
            return httpx.Response(400, json={'error': {'code': 'json_validate_failed'}})
        if kind == 'outer_json':
            return httpx.Response(200, text='not JSON')
        content = {'null_content': None, 'local_json': '{broken', 'local_schema': '{"value":99}'}[kind]
        return httpx.Response(200, json={'choices': [{'message': {'content': content}}], 'usage': {'total_tokens': 3}})
    async def wait(_):
        pass
    monkeypatch.setattr('landlaw.provider.asyncio.sleep', wait)
    provider = GroqProvider(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(respond)), request_budget=ledger)
    try:
        with pytest.raises(ProviderUnavailable) as error:
            await provider.generate(Bounded, 'Return JSON', {}, Budget())
        assert error.value.format_failure is True and len(calls) == 2
        assert ledger.summary()['reserved_budget'] == 0
    finally:
        await provider.close()


async def test_transport_failure_retains_estimate_and_stops_at_test_cap(settings, store, monkeypatch):
    calls = []
    ledger = RequestBudget(max_requests=1)
    def respond(request):
        calls.append(request)
        raise httpx.ConnectError('synthetic failure')
    async def wait(_):
        pass
    monkeypatch.setattr('landlaw.provider.asyncio.sleep', wait)
    provider = GroqProvider(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(respond)), request_budget=ledger)
    try:
        with pytest.raises(BudgetExceeded):
            await provider.generate(Probe, 'Return JSON', {}, Budget())
        assert len(calls) == 1
        assert ledger.summary()['estimated_usage'] > 0
    finally:
        await provider.close()


async def test_persistence_error_prevents_network_io(settings, store, monkeypatch):
    calls = []
    ledger = RequestBudget()
    def fail_write():
        raise OSError('synthetic persistence failure')
    monkeypatch.setattr(ledger, 'persist', fail_write)
    def respond(request):
        calls.append(request)
        return httpx.Response(200)
    provider = GroqProvider(settings, store, httpx.AsyncClient(transport=httpx.MockTransport(respond)), request_budget=ledger)
    try:
        with pytest.raises(OSError):
            await provider.generate(Probe, 'Return JSON', {}, Budget())
        assert calls == []
    finally:
        await provider.close()


async def test_operator_suite_stops_after_hard_cap_and_keeps_denominator(settings, store, tmp_path, monkeypatch):
    from datetime import date
    from types import SimpleNamespace

    from conftest import release
    from landlaw import evaluation
    from landlaw.models import ChatResult
    release(store)
    settings = settings.model_copy(update={'reports_dir': tmp_path / 'reports'})
    rows = [{'id': ident, 'question': ident, 'as_of': '2024-08-02', 'rubric': []}
            for ident in ('BUDGET_FIRST', 'MUST_NOT_START')]
    monkeypatch.setattr(evaluation, 'frozen_dataset', lambda *_: (rows, 'fixture-suite'))
    monkeypatch.setattr(evaluation, 'validate_suite_corpus', lambda *_: None)
    ledger = RequestBudget(max_tokens=1)
    async def generate(*args):
        raise AssertionError('No model call in evaluation-stop fixture')
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail('No HTTP expected')))
    provider = SimpleNamespace(settings=settings, configured=True, client=client, generate=generate, request_budget=ledger)
    seen = []
    class FakeAgent:
        def __init__(self, *args):
            pass
        async def run(self, request, emit, release_id):
            seen.append(request.message)
            with pytest.raises(BudgetExceeded):
                ledger.reserve(wire())
            return ChatResult(status='limited', content='Test cap reached', as_of=date(2024, 8, 2),
                trace_id='fixture', model=settings.generation_model, embedding_model=settings.embedding_model,
                mode='agentic', corpus_release=release_id)
    monkeypatch.setattr(evaluation, 'Agent', FakeAgent)
    try:
        result = await evaluation.evaluate(settings, store, provider)
        assert seen == ['BUDGET_FIRST']
        assert result['cases'] == 2
        assert result['acceptance_passed'] is False
    finally:
        await client.aclose()


def test_pilot_allocation_reports_confirmed_usage_and_resumes(tmp_path):
    from scripts.evaluate_agentic_pilot import PilotAllocation
    path = tmp_path / 'pilot-budget.json'
    ledger = PilotAllocation(path, 'post-hotfix-pilot', max_requests=10,
                             max_tokens=30000, per_request=3000)
    ident = ledger.reserve({'messages': []})
    ledger.settle(ident, {'total_tokens': 123}, status_code=200)
    assert ledger.summary()['confirmed_usage'] == 123
    assert ledger.summary()['reported_actual_tokens'] == 123
    assert ledger.summary()['requests_reserved'] == 1
    assert PilotAllocation(path, 'post-hotfix-pilot', max_requests=10,
                           max_tokens=30000, per_request=3000).summary()['confirmed_usage'] == 123


async def test_resumed_blocked_evaluation_never_starts_a_case(settings, store, monkeypatch):
    from types import SimpleNamespace

    from landlaw import evaluation
    ledger = RequestBudget(max_tokens=1)
    with pytest.raises(BudgetExceeded):
        ledger.reserve(wire())
    provider = SimpleNamespace(generate=None, request_budget=ledger)
    def must_not_start(*args):
        pytest.fail('A blocked budget must stop before reading/running the suite')
    monkeypatch.setattr(evaluation, 'frozen_dataset', must_not_start)
    with pytest.raises(BudgetExceeded):
        await evaluation.evaluate(settings, store, provider)
