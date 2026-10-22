"""Standing verified snapshot: reviewed passages survive operational date boundaries.

These tests use isolated SQLite and a deterministic provider. They do not call a
model and do not change the legacy version-1 scoped-gate behavior.
"""
import asyncio
import hashlib
import json
from datetime import date, timedelta

import pytest

from conftest import document, release, session
from landlaw.models import ChatRequest, Chunk
from landlaw.ops import activate_source_gate, build_standing_policy
from landlaw.security import digest, local_date, utcnow
from landlaw.simple_rag import SimpleAnswer, SimpleRAG
from test_scoped_source_gate import install_gate
from test_source_review_policy import review


class SnapshotProvider:
    configured = True

    def __init__(self, settings):
        self.settings = settings
        self.embeds = 0
        self.generations = 0

    async def embed(self, *args, **kwargs):
        self.embeds += 1
        return []

    async def generate(self, schema, instruction, payload, budget, **kwargs):
        self.generations += 1
        budget.llm()
        assert payload["allowed_citation_ids"]
        return SimpleAnswer(answer="Điều kiện bồi thường cần được xem xét theo hồ sơ [S1].")


def install_standing(store, payload, doc, tmp_path, *, start=None, end=None):
    install_gate(store, payload, doc, tmp_path, start=start, end=end)
    base = store.source_gate(payload['id'])
    policy = build_standing_policy(store, base)
    path = tmp_path / 'standing-policy.json'
    path.write_text(json.dumps(policy, ensure_ascii=False, sort_keys=True))
    activate_source_gate(store, path)
    return base, policy


def request(session_id, message, as_of):
    return ChatRequest(session_id=session_id, message=message, as_of=as_of, mode="simple_rag")


def test_build_is_deterministic_and_activation_is_reversible(store, settings, tmp_path):
    doc = document()
    payload = release(store, [doc])
    install_gate(store, payload, doc, tmp_path)
    base = store.source_gate(payload['id'])
    first = build_standing_policy(store, base)
    second = build_standing_policy(store, base)
    assert first == second
    assert first['version'] == 2 and first['mode'] == 'standing_verified_snapshot'
    assert first['supersedes']['policy_sha256'] == hashlib.sha256(
        json.dumps(base, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    entry = first['standing'][doc.id]
    assert entry['receipt_sha256'] == base['receipts'][doc.id]
    assert entry['standing_chunks'] == {doc.chunks[0].id: doc.chunks[0].checksum}
    assert entry['legal_windows'] == []
    path = tmp_path / 'candidate.json'
    path.write_text(json.dumps(first, ensure_ascii=False, sort_keys=True))
    assert activate_source_gate(store, path)['policy_sha256']
    assert store.source_gate(payload['id'])['version'] == 2
    # Explicit rollback restores the preserved v1 policy without touching receipts.
    store.set_state('source_gate:' + payload['id'], json.dumps(base, ensure_ascii=False, sort_keys=True))
    assert store.source_gate(payload['id'])['version'] == 1
    assert store.source_gate_status(payload, date(2026, 10, 22))['mode'] == 'scoped_receipts'


@pytest.mark.parametrize('target', [
    date(2026, 10, 22), date(2026, 10, 23), date(2026, 10, 25),
    date(2026, 11, 1), date(2027, 10, 22),
])
def test_standing_passage_is_usable_across_operational_boundaries(store, settings, tmp_path, target):
    doc = document()
    payload = release(store, [doc])
    install_standing(store, payload, doc, tmp_path)
    status = store.source_gate_status(payload, target)
    assert status['mode'] == 'standing_verified_snapshot'
    assert status['usable'] and status['eligible_passages'] == 1
    assert status['reviewed_at'] and status['operational_expiry'] is None
    state = store.scoped_source_reviews(
        payload, [(doc.id, doc.chunks[0].id, doc.chunks[0].checksum)], target)
    assert state[doc.id + ':' + doc.chunks[0].id] == 'standing'


def test_aged_receipt_does_not_expire_a_standing_passage(store, settings, tmp_path):
    doc = document()
    payload = release(store, [doc])
    install_standing(store, payload, doc, tmp_path)
    row = store.rows('SELECT * FROM source_reviews')[0]
    value = json.loads(row['receipt'])
    value['checked_at'] = (utcnow() - timedelta(days=400)).isoformat()
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True)
    ident = hashlib.sha256(canonical.encode()).hexdigest()
    with store.transaction() as conn:
        store.execute(conn, 'UPDATE source_reviews SET id=?,checked_at=?,receipt=?',
                      (ident, value['checked_at'], canonical))
        store.execute(conn, 'UPDATE app_state SET value=? WHERE key=?',
                      (json.dumps({'version': 2, 'mode': 'standing_verified_snapshot',
                                   'release_id': payload['id'],
                                   'supersedes': {'version': 1, 'policy_sha256': '0' * 64},
                                   'receipts': {doc.id: ident},
                                   'standing': {doc.id: {
                                       'receipt_sha256': ident,
                                       'reviewed_at': value['checked_at'],
                                       'reviewed_as_of': value['checked_at'][:10],
                                       'chunks': {doc.chunks[0].id: doc.chunks[0].checksum},
                                       'standing_chunks': {doc.chunks[0].id: doc.chunks[0].checksum},
                                       'legal_windows': []}}}, ensure_ascii=False, sort_keys=True),
                       'source_gate:' + payload['id']))
    status = store.source_gate_status(payload, date(2027, 1, 1))
    assert status['usable'] and status['eligible_passages'] == 1
    assert status['reviewed_at'] == value['checked_at']


def test_simple_rag_uses_standing_evidence_after_the_old_review_date(store, settings, tmp_path):
    doc = document(text="Điều kiện bồi thường khi thu hồi đất cần giấy chứng nhận và hồ sơ.")
    payload = release(store, [doc])
    install_standing(store, payload, doc, tmp_path)
    sid, _ = session(store)
    provider = SnapshotProvider(settings)
    result = asyncio.run(SimpleRAG(store, provider).run(
        request(sid, "Điều kiện bồi thường khi thu hồi đất là gì?", date(2026, 11, 1)),
        lambda _: None, payload['id']))
    assert result.status == "answered"
    assert provider.embeds == 1 and provider.generations == 1
    assert result.citations and result.citations[0].id == doc.chunks[0].id
    assert "đối chiếu đến" in result.content
    assert result.source_context['source_review_mode'] == 'standing_verified_snapshot'


def test_latest_adverse_review_still_invalidates_standing_evidence(store, settings, tmp_path):
    doc = document()
    payload = release(store, [doc])
    install_standing(store, payload, doc, tmp_path)
    assert store.source_gate_status(payload, date(2026, 11, 1))['eligible_passages'] == 1
    review(store, payload, doc, 'changed')
    status = store.source_gate_status(payload, date(2026, 11, 1))
    assert status['eligible_passages'] == 0 and not status['usable']
    state = store.scoped_source_reviews(payload,
        [(doc.id, doc.chunks[0].id, doc.chunks[0].checksum)], date(2026, 11, 1))
    assert state[doc.id + ':' + doc.chunks[0].id] == 'changed'


def test_missing_receipt_and_changed_content_fail_closed(store, settings, tmp_path):
    doc = document()
    payload = release(store, [doc])
    install_standing(store, payload, doc, tmp_path)
    with store.transaction() as conn:
        store.execute(conn, 'DELETE FROM source_reviews')
    assert store.source_gate_status(payload, date(2026, 11, 1))['eligible_passages'] == 0
    assert not store.source_gate_status(payload, date(2026, 11, 1))['usable']


def test_changed_chunk_checksum_is_not_admitted(store, settings, tmp_path):
    doc = document()
    payload = release(store, [doc])
    install_standing(store, payload, doc, tmp_path)
    with store.transaction() as conn:
        store.execute(conn, 'UPDATE chunks SET checksum=? WHERE id=?',
                      (digest('tampered'), doc.chunks[0].id))
    assert store.source_gate_status(payload, date(2026, 11, 1))['eligible_passages'] == 0


def test_unreviewed_passage_is_not_admitted_by_a_standing_policy(store, settings, tmp_path):
    doc = document()
    doc.chunks.append(Chunk(id=doc.id + '-2', document_id=doc.id, locator='Điều 2',
                            text='Đoạn chưa được review.', checksum=digest('Đoạn chưa được review.')))
    payload = release(store, [doc])
    install_standing(store, payload, doc, tmp_path)
    now = date(2026, 11, 1)
    state = store.scoped_source_reviews(payload,
        [(doc.id, doc.chunks[0].id, doc.chunks[0].checksum),
         (doc.id, doc.chunks[1].id, doc.chunks[1].checksum)], now)
    assert state[doc.id + ':' + doc.chunks[0].id] == 'standing'
    assert state[doc.id + ':' + doc.chunks[1].id] == 'unknown'
    assert store.source_gate_status(payload, now)['eligible_passages'] == 1


def test_long_legal_window_is_preserved_and_not_expanded(store, settings, tmp_path):
    doc = document()
    payload = release(store, [doc])
    install_standing(store, payload, doc, tmp_path,
                     start=date(2024, 8, 1), end=date(2025, 1, 1))
    policy = store.source_gate(payload['id'])
    entry = policy['standing'][doc.id]
    assert entry['standing_chunks'] == {}
    assert entry['legal_windows'] == [{'as_of_from': '2024-08-01', 'as_of_to': '2025-01-01',
                                       'chunk_checksums': {doc.chunks[0].id: doc.chunks[0].checksum}}]
    assert store.source_gate_status(payload, date(2024, 9, 1))['eligible_passages'] == 1
    assert store.source_gate_status(payload, date(2026, 11, 1))['eligible_passages'] == 0
    state = store.scoped_source_reviews(payload,
        [(doc.id, doc.chunks[0].id, doc.chunks[0].checksum)], date(2024, 9, 1))
    assert state[doc.id + ':' + doc.chunks[0].id] == 'reviewed_window'


def test_repealed_and_future_documents_are_removed_by_legal_applicability(store, settings, tmp_path):
    repealed = document(doc_id='repealed').model_copy(update={
        'effective_from': date(2024, 8, 1), 'effective_to': date(2026, 1, 1)})
    future = document(doc_id='future').model_copy(update={
        'effective_from': date(2027, 1, 1)})
    payload = release(store, [repealed, future])
    from landlaw.ops import record_source_review

    def receipt_for(doc, name):
        receipt = {'document_id': doc.id, 'checksum': doc.checksum,
                   'checked_at': utcnow().isoformat(), 'status': 'unchanged',
                   'evidence_urls': [str(doc.url)],
                   'relation_review': 'Reviewed only the named passages and date interval.',
                   'verified_scope': [{'as_of_from': str(local_date()),
                                       'as_of_to': str(local_date() + timedelta(days=1)),
                                       'chunk_checksums': {doc.chunks[0].id: doc.chunks[0].checksum}}]}
        path = tmp_path / name
        path.write_text(json.dumps(receipt))
        return record_source_review(store, path)['receipt_sha256']

    v1 = {'version': 1, 'release_id': payload['id'],
          'receipts': {repealed.id: receipt_for(repealed, 'repealed.json'),
                       future.id: receipt_for(future, 'future.json')}}
    path = tmp_path / 'v1.json'
    path.write_text(json.dumps(v1))
    activate_source_gate(store, path)
    policy = build_standing_policy(store)
    path = tmp_path / 'v2.json'
    path.write_text(json.dumps(policy, ensure_ascii=False, sort_keys=True))
    activate_source_gate(store, path)
    # Repealed document is eligible while it was in force and removed afterwards.
    assert store.source_gate_status(payload, date(2025, 1, 1))['eligible_passages'] == 1
    assert store.source_gate_status(payload, date(2026, 6, 1))['eligible_passages'] == 0
    # Future-effective document is not admitted before it takes effect.
    assert store.source_gate_status(payload, date(2026, 11, 1))['eligible_passages'] == 0
    assert store.source_gate_status(payload, date(2027, 2, 1))['eligible_passages'] == 1


def test_activation_refuses_to_drop_a_pinned_receipt(store, tmp_path):
    from landlaw.ops import record_source_review

    first, second = document(), document('other')
    payload = release(store, [first, second])
    receipts = {}
    for doc in (first, second):
        receipt = {'document_id': doc.id, 'checksum': doc.checksum,
                   'checked_at': utcnow().isoformat(), 'status': 'unchanged',
                   'evidence_urls': [str(doc.url)],
                   'relation_review': 'Reviewed the named passage and date interval.',
                   'verified_scope': [{'as_of_from': str(local_date()),
                                       'as_of_to': str(local_date() + timedelta(days=1)),
                                       'chunk_checksums': {doc.chunks[0].id: doc.chunks[0].checksum}}]}
        path = tmp_path / f'{doc.id}-receipt.json'
        path.write_text(json.dumps(receipt))
        receipts[doc.id] = record_source_review(store, path)['receipt_sha256']
    v1_path = tmp_path / 'v1-two-docs.json'
    v1_path.write_text(json.dumps({'version': 1, 'release_id': payload['id'], 'receipts': receipts}))
    activate_source_gate(store, v1_path)
    policy = build_standing_policy(store)
    policy['receipts'].pop(second.id)
    policy['standing'].pop(second.id)
    path = tmp_path / 'dropped-receipt.json'
    path.write_text(json.dumps(policy, ensure_ascii=False, sort_keys=True))
    with pytest.raises(ValueError, match='exact v1 receipt cohort'):
        activate_source_gate(store, path)
    assert store.source_gate(payload['id'])['version'] == 1


def test_activation_refuses_to_drop_a_reviewed_passage(store, tmp_path):
    from landlaw.models import Chunk
    from landlaw.ops import record_source_review

    doc = document()
    second_text = 'Điều 2. Hồ sơ bồi thường phải được đối chiếu.'
    doc.chunks.append(Chunk(id='law-2', document_id=doc.id, locator='Điều 2',
                            text=second_text, checksum=digest(second_text)))
    payload = release(store, [doc])
    receipt = {
        'document_id': doc.id, 'checksum': doc.checksum,
        'checked_at': utcnow().isoformat(), 'status': 'unchanged',
        'evidence_urls': [str(doc.url)],
        'relation_review': 'Reviewed both passages and the date interval.',
        'verified_scope': [{'as_of_from': str(local_date()),
                            'as_of_to': str(local_date() + timedelta(days=1)),
                            'chunk_checksums': {chunk.id: chunk.checksum for chunk in doc.chunks}}],
    }
    receipt_path = tmp_path / 'two-passages.json'
    receipt_path.write_text(json.dumps(receipt))
    ident = record_source_review(store, receipt_path)['receipt_sha256']
    v1_path = tmp_path / 'v1-two.json'
    v1_path.write_text(json.dumps({'version': 1, 'release_id': payload['id'],
                                   'receipts': {doc.id: ident}}))
    activate_source_gate(store, v1_path)
    policy = build_standing_policy(store)
    entry = policy['standing'][doc.id]
    assert set(entry['chunks']) == {'law-1', 'law-2'}
    entry['chunks'].pop('law-2')
    entry['standing_chunks'].pop('law-2', None)
    path = tmp_path / 'dropped-passage.json'
    path.write_text(json.dumps(policy, ensure_ascii=False, sort_keys=True))
    with pytest.raises(ValueError, match='preserve every reviewed passage'):
        activate_source_gate(store, path)
    assert store.source_gate(payload['id'])['version'] == 1
