"""Offline checks of the pilot harness; no external requests or legal scoring."""
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

spec = importlib.util.spec_from_file_location('pilot_runner', Path(__file__).with_name('runner.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_reserves_before_request_and_refunds_only_reported_usage():
    gate = runner.TokenGate()
    reserved = gate.reserve('C01', 1000, 2048)
    assert reserved == 7144 and gate.charged == reserved
    gate.settle(reserved, {'total_tokens': 500})
    assert gate.charged == gate.observed == 500


def test_unknown_usage_keeps_full_bound():
    gate = runner.TokenGate()
    reserved = gate.reserve('C01', 1000, 2048)
    gate.settle(reserved, {})
    assert gate.charged == reserved and gate.unknown == 1


def test_token_cap_prevents_request_count_increment():
    gate = runner.TokenGate()
    gate.charged = 55000
    with pytest.raises(runner.PilotBudget, match='pilot_token_cap'):
        gate.reserve('C01', 1, 2048)
    assert gate.requests == 0 and gate.charged == 55000


def test_six_per_case_and_eighteen_total_include_retry():
    gate = runner.TokenGate()
    for case in ['C01', 'C02', 'C03']:
        for _ in range(6):
            gate.settle(gate.reserve(case, 1, 2048), {'total_tokens': 1})
        with pytest.raises(runner.PilotBudget, match='pilot_request_cap'):
            gate.reserve(case, 1, 2048)
    with pytest.raises(runner.PilotBudget, match='pilot_request_cap'):
        gate.reserve('OTHER', 1, 2048)
    assert gate.requests == 18


def test_invalid_usage_not_accepted_as_zero():
    for usage in [{'total_tokens': -1}, {'total_tokens': True}, {'total_tokens': '1'}]:
        gate = runner.TokenGate()
        reserved = gate.reserve('C01', 1000, 2048)
        gate.settle(reserved, usage)
        assert gate.charged == reserved and gate.unknown == 1


def test_bound_violation_fails_closed():
    gate = runner.TokenGate()
    reserved = gate.reserve('C01', 1000, 2048)
    with pytest.raises(runner.PilotBudget, match='usage_exceeded_conservative_bound'):
        gate.settle(reserved, {'total_tokens': reserved + 1})


def request_body():
    return {'model': 'openai/gpt-oss-120b', 'temperature': 0, 'max_completion_tokens': 2048,
            'tool_choice': 'none', 'messages': [{'role': 'user', 'content': json.dumps(
                {'question': 'Synthetic question', 'history': [], 'evidence': [], 'documents': []})}],
            'response_format': {'json_schema': {'name': 'Draft'}}}


class NoCooldown:
    def cooldown(self):
        return 0


@pytest.mark.asyncio
async def test_capture_actual_body_and_visible_response_only(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'OUT', tmp_path)
    seen = []
    def mock(request):
        seen.append(request.content)
        return httpx.Response(200, json={'model': 'openai/gpt-oss-120b',
            'usage': {'total_tokens': 10}, 'choices': [{'index': 0, 'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': '{}', 'reasoning': 'Hidden test value'}}]})
    gate = runner.TokenGate()
    context = {'case': {'id': 'C01', 'question': 'Synthetic question'}, 'expected': [], 'store': NoCooldown()}
    transport = runner.ControlledTransport(lambda: None, gate, context, [], httpx.MockTransport(mock))
    body = request_body()
    async with httpx.AsyncClient(transport=transport) as client:
        await client.post('https://api.groq.com/openai/v1/chat/completions', json=body)
    assert len(seen) == 1 and json.loads(seen[0]) == body
    recorded = json.loads((tmp_path / 'C01/wire/01/request.json').read_text())
    assert recorded == body
    response = (tmp_path / 'C01/wire/01/response.json').read_text()
    assert 'Hidden test value' not in response
    assert gate.charged == 10


@pytest.mark.asyncio
async def test_token_block_happens_before_underlying_transport(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'OUT', tmp_path)
    calls = []
    def mock(request):
        calls.append(request)
        raise AssertionError('Must never reach transport')
    gate = runner.TokenGate()
    gate.charged = 59999
    context = {'case': {'id': 'C01', 'question': 'Synthetic question'}, 'expected': [], 'store': NoCooldown()}
    transport = runner.ControlledTransport(lambda: None, gate, context, [], httpx.MockTransport(mock))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(runner.PilotBudget, match='pilot_token_cap'):
            await client.post('https://api.groq.com/openai/v1/chat/completions', json=request_body())
    assert calls == [] and gate.requests == 0
