"""Regression tests for the live demo runner's single-loop contract."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from landlaw.config import Settings


def load_runner():
    path = Path(__file__).parents[1] / 'scripts' / 'evaluate_demo_suite.py'
    spec = importlib.util.spec_from_file_location('demo_evaluation_runner_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_live_legal_cases_use_one_loop_and_preserve_harness_errors(monkeypatch):
    runner = load_runner()
    loop_ids, closed = set(), []

    class FakeProvider:
        configured = True

        def __init__(self, *args, **kwargs):
            pass

        async def close(self):
            closed.append(True)

    async def fake_run(case, store, provider, allocation):
        loop_ids.add(id(asyncio.get_running_loop()))
        if case['id'] == 'L02':
            raise RuntimeError('simulated harness failure')
        return {'id': case['id'], 'kind': 'legal', 'execution': 'RUN', 'llm_calls': 1}

    monkeypatch.setattr(runner, 'GroqProvider', FakeProvider)
    monkeypatch.setattr(runner, 'run_legal_live', fake_run)
    cases = [{'id': f'L{i:02d}', 'kind': 'legal'} for i in range(1, 6)]
    records = asyncio.run(runner.run_live_legal_cases(
        cases, Settings(), None, SimpleNamespace(entries=[]), 0))

    assert len(records) == 5
    assert len(loop_ids) == 1
    assert closed == [True]
    assert records[1]['execution'] == 'ERROR'
    assert records[1]['reason'] == 'HARNESS_ERROR'
    assert [record['id'] for record in records] == [case['id'] for case in cases]
