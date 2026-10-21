"""Judge evaluation must never open the operator's serving database."""
import json
from pathlib import Path
from types import SimpleNamespace
from datetime import timedelta

import pytest
from pydantic import SecretStr

from landlaw.store import Store
from landlaw.security import utcnow
from scripts import evaluate_faithfulness as evaluation


@pytest.mark.parametrize('owner_configured', [False, True])
@pytest.mark.parametrize('cooldown_seconds', [0, 3600])
async def test_faithfulness_uses_disposable_sqlite_even_with_serving_credentials(
        tmp_path, settings, monkeypatch, owner_configured, cooldown_seconds):
    dangerous = settings.model_copy(update={
        'database_url': SecretStr('postgresql://serving-do-not-connect'),
        'admin_database_url': SecretStr('postgresql://owner-do-not-connect' if owner_configured else '')})
    monkeypatch.setattr(evaluation, 'Settings', lambda: dangerous)
    opened = []
    instances = []

    def guarded_store(selected):
        assert not selected.database_url.get_secret_value()
        assert not selected.admin_database_url.get_secret_value()
        assert selected.sqlite_path != dangerous.sqlite_path
        opened.append(Path(selected.sqlite_path))
        return Store(selected)

    class FakeJudge:
        def __init__(self, selected, store, *, usage_scope):
            assert usage_scope == 'operator'
            assert selected.generation_model == settings.generation_model
            self.client = SimpleNamespace(event_hooks={})
            self.closed = False
            self.calls = 0
            instances.append(self)

        async def generate(self, schema, instruction, payload, budget, **kwargs):
            self.calls += 1
            budget.llm()
            return schema(claims=[evaluation.JudgedClaim(
                statement='Nội dung giả lập được nguồn hỗ trợ.', supported=True,
                evidence_ids=['C1'], reason='Fixture kiểm tra isolation, không chấm luật thật.')])

        async def close(self):
            self.closed = True

    monkeypatch.setattr(evaluation, 'Store', guarded_store)
    monkeypatch.setattr(evaluation, 'GroqProvider', FakeJudge)
    run = tmp_path/'run'
    run.mkdir()
    (run/'metadata.json').write_text(json.dumps({'configuration_sha256':'evaluated-configuration'}))
    (run/'records.json').write_text(json.dumps([{
        'case_id':'S07', 'evaluation_context':[{'citation_id':'C1','text':'Nguồn giả lập công khai.'}],
        'result':{'corpus_release':'fixture','model':settings.generation_model,
                  'status':'answered','content':'Nội dung giả lập được nguồn hỗ trợ.'}}]))
    output = tmp_path/'faithfulness.json'
    if cooldown_seconds:
        not_before=utcnow()+timedelta(seconds=cooldown_seconds)
        (tmp_path/'operator-cooldown.json').write_text(json.dumps({'not_before':not_before.isoformat()}))
    await evaluation.main([run], output)
    assert len(opened) == 1 and not opened[0].exists()
    assert all(instance.closed for instance in instances)
    assert not Path(dangerous.sqlite_path).exists()
    report = json.loads(output.read_text())
    assert report['configuration_sha256'] == 'evaluated-configuration'
    assert report['judge_storage_backend'] == 'isolated_sqlite'
    assert report['results'][2]['status'] == 'missing_case'  # S06 is not injected or re-run.
    assert instances[0].calls == (0 if cooldown_seconds else 1)
    assert report['results'][3]['status'] == ('judge_error' if cooldown_seconds else 'scored')
    if cooldown_seconds:
        assert (tmp_path/'operator-cooldown.json').exists()
