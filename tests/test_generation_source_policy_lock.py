"""Evaluation must bind the same scoped receipts it will actually use."""
import json
from pathlib import Path

import pytest
from conftest import document, release
from test_scoped_source_gate import install_gate
from scripts.evaluate_generation_candidate import lock_source_policy
from landlaw.store import Store


def test_restored_candidate_requires_receipts_and_locks_exact_source_cohort(store, settings, tmp_path):
    doc = document(); payload = release(store, [doc])
    install_gate(store, payload, doc, tmp_path)
    backup = tmp_path/'backup.json'; store.backup(backup)
    restored = Store(settings.model_copy(update={'sqlite_path': str(tmp_path/'restored.db')}))
    output = tmp_path/'output'; output.mkdir()
    try:
        restored.restore(backup)
        with pytest.raises(ValueError, match='requires recent'):
            lock_source_policy(restored, backup, [], None, output)
        first = lock_source_policy(restored, backup, [tmp_path/'receipt.json'], None, output)
        assert first['source_gate_sha256'] == store.source_gate_status(payload)['policy_sha256']
        assert first == lock_source_policy(restored, backup, [tmp_path/'receipt.json'], None, output)
        # Even equivalent reformatting changes the locked evidence bytes.
        path = tmp_path/'receipt.json'; value = json.loads(path.read_text())
        path.write_text(json.dumps(value, indent=2)+'\n')
        with pytest.raises(ValueError, match='cohort changed'):
            lock_source_policy(restored, backup, [path], None, output)
    finally: restored.close()


def test_historical_unbound_runs_cannot_be_silently_adopted(store, tmp_path):
    release(store, [document()]); backup = tmp_path/'backup.json'; store.backup(backup)
    output = tmp_path/'output'; (output/'runs/old').mkdir(parents=True)
    (output/'runs/old/records.json').write_text('[]')
    with pytest.raises(ValueError, match='Historical run'):
        lock_source_policy(store, backup, [], None, output)
