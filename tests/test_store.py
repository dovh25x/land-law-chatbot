import concurrent.futures
import json
from datetime import timedelta

import pytest

from landlaw.security import utcnow
from landlaw.store import RateLimited, Store
from conftest import document, release, session


def test_session_isolation_hash_expiry_and_restart(store, settings):
    sid, token = session(store)
    other, other_token = session(store)
    assert store.authenticate(sid, token)
    assert not store.authenticate(sid, other_token)
    assert store.rows("SELECT token_hash FROM sessions WHERE id=?", (sid,))[0]["token_hash"] != token
    reopened = Store(settings)
    assert reopened.authenticate(sid, token)
    reopened.close()
    with store.transaction() as conn:
        store.execute(conn, "UPDATE sessions SET created_at=? WHERE id=?", ((utcnow()-timedelta(days=8)).isoformat(), sid))
    assert not store.authenticate(sid, token)
    store.cleanup()
    assert store.authenticate(other, other_token)


def test_counters_atomic_and_concurrent(store):
    def consume(_):
        try:
            store.consume([("shared", 3, 60)])
            return True
        except RateLimited:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(consume, range(20))) == 3
    with pytest.raises(RateLimited):
        store.consume([("fresh", 3, 60), ("shared", 3, 60)])
    assert not store.rows("SELECT * FROM counters WHERE key='fresh'")


def test_release_immutable_backup_restore_and_rollback(store, settings, tmp_path):
    release(store)
    with pytest.raises(ValueError):
        release(store)
    release(store, [document("new")], "r2")
    assert store.state("previous_release") == "r1"
    backup = tmp_path / "backup.json"
    store.backup(backup)
    assert "sessions" not in json.loads(backup.read_text())
    restored = Store(settings.model_copy(update={"sqlite_path": str(tmp_path / "restored.db")}))
    restored.restore(backup)
    assert restored.state("active_release") == "r2"
    assert restored.document("new")
    restored.publish(restored.state("previous_release"))
    assert restored.document("law")
    restored.close()


def test_search_keeps_national_law_but_filters_other_projects(store):
    national = document()
    ring = document("ring", project="ring4")
    olympic = document("oly", project="olympic")
    release(store, [national, ring, olympic])
    results = store.search("boi thuong", project="ring4")
    assert {r.document.id for r in results} == {"law", "ring"}


def test_encrypted_restore_preserves_session_isolation_and_rejects_plaintext_sessions(store, settings, tmp_path):
    from cryptography.fernet import Fernet
    from landlaw.store import Store
    from pydantic import SecretStr
    from conftest import session, release
    release(store)
    sid, token = session(store)
    output = tmp_path / 'sessions.enc'
    with pytest.raises(ValueError):
        store.backup(output, include_sessions=True)
    store.settings = settings.model_copy(update={'backup_encryption_key': SecretStr(Fernet.generate_key().decode())})
    store.backup(output, include_sessions=True)
    assert not output.read_bytes().startswith(b'{') and token.encode() not in output.read_bytes()
    restored = Store(store.settings.model_copy(update={'sqlite_path': str(tmp_path / 'restored.db')}))
    restored.restore(output)
    assert restored.authenticate(sid, token)
    assert not restored.authenticate(sid, 'another-token')
    assert restored.state('active_release') == 'r1'
    restored.close()
