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


def test_embedding_batch_counts_inputs_atomically(store):
    store.consume_weighted([('batch-http',5,60,1),('batch-inputs',10,60,8)])
    with pytest.raises(RateLimited):
        store.consume_weighted([('batch-http',5,60,1),('batch-inputs',10,60,8)])
    assert store.rows("SELECT value FROM counters WHERE key='batch-http'")[0]['value'] == 1
    assert store.rows("SELECT value FROM counters WHERE key='batch-inputs'")[0]['value'] == 8


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


def test_exact_article_number_retrieves_without_keyword_overlap(store):
    doc = document()
    doc.document_number = "40/2026/QĐ-UBND"
    doc.chunks[0].locator = "Điều 29"
    doc.chunks[0].text = "Nội dung hồ sơ cũ còn được xem xét theo thủ tục."
    release(store, [doc])
    found = store.search("Điều 29 của 40/2026/QĐ-UBND")
    assert found and found[0].chunk.locator == "Điều 29"
    assert not store.documents()[0].chunks
    assert "chunks" not in store.release(metadata_only=True)["documents"][0]


def test_primary_retrieval_keeps_leaf_passage_and_parent_remains_openable(store):
    doc=document(text='Điều 1. Điều kiện bồi thường khi thu hồi đất.')
    child=doc.chunks[0].model_copy(update={'parent_id':'law-0-parent'})
    parent=child.model_copy(update={'id':'law-0-parent','parent_id':None,
        'locator':'Điều 1 · ngữ cảnh','text':child.text+' Bồi thường khi thu hồi đất. '*30})
    doc.chunks=[child,parent]
    release(store,[doc])
    hits=store.search('bồi thường thu hồi đất')
    assert [h.chunk.id for h in hits]==[child.id]
    assert store.chunk(parent.id).text==parent.text


def test_open_article_and_search_distinguish_added_article_suffix(store):
    law = document()
    law.document_number = '124/2020/NĐ-CP'
    original = law.chunks[0].model_copy(update={'locator':'Điều 28','text':'Thủ tục ban đầu.'})
    added = original.model_copy(update={'id':'law-added','locator':'Điều 28a','text':'Thủ tục bổ sung khác.'})
    law.chunks = [original, added]
    release(store,[law])
    assert [c.id for c in store.open_document('law',locator='Điều 28a').chunks] == ['law-added']
    assert [c.id for c in store.open_document('law',locator='Điều 28').chunks] == [original.id]
    assert store.search('Điều 28a của 124/2020/NĐ-CP')[0].chunk.id == 'law-added'


def test_effectivity_tool_opens_operative_article_not_preamble(store):
    from landlaw.models import Chunk
    from landlaw.security import digest
    doc=document()
    texts=[('preamble','Căn cứ văn bản khác có hiệu lực ngày 01/01/2020.'),
           ('operative','Điều 260. Luật này có hiệu lực thi hành từ ngày 01 tháng 8 năm 2024.')]
    doc.chunks=[Chunk(id=key,document_id=doc.id,text=text,locator='Điều 260' if key=='operative' else 'Mở đầu',
        checksum=digest(text)) for key,text in texts]
    release(store,[doc])
    assert [c.id for c in store.open_effectivity(doc.id).chunks]==['operative']


def test_open_article_preserves_late_clause_and_other_requested_article(store):
    from landlaw.models import Chunk
    from landlaw.security import digest
    doc = document()
    doc.chunks = []
    for index in range(12):
        text = f'{index + 1}. Quy định về thủ tục.'
        if index == 11:
            text = '13. Hồ sơ đã có phương án bồi thường phê duyệt tiếp tục thực hiện theo điều khoản chuyển tiếp.'
        doc.chunks.append(Chunk(id=f'part-{index:02}', document_id=doc.id, text=text,
                                locator='Điều 3', page=index + 1, checksum=digest(text)))
    text = 'Điều 13. Nghị quyết này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2026.'
    doc.chunks.append(Chunk(id='effectivity', document_id=doc.id, text=text, locator='Điều 13', page=15, checksum=digest(text)))
    release(store, [doc])
    opened = store.open_document(doc.id, locator='Khoản 13 Điều 3', query='phương án đã phê duyệt và chuyển tiếp')
    assert opened.chunks[0].id == 'part-11'
    opened = store.open_document(doc.id, locator='Điều 3 và Điều 13', query='phương án đã phê duyệt và chuyển tiếp')
    assert {chunk.id for chunk in opened.chunks} >= {'part-11', 'effectivity'}
    assert len(opened.chunks) <= 3


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
