"""A scoped release admits only exact reviewed passages at reviewed dates."""
import hashlib
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from conftest import document, release
from test_agent import FakeProvider, noop
from test_source_review_policy import approved_state, review
from landlaw.agent import Agent
from landlaw.api import create_app
from landlaw.models import ChatRequest, Chunk
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.security import digest, local_date, utcnow
from landlaw.store import Store


def install_gate(store, payload, doc, tmp_path, *, start=None, end=None):
    receipt = {'document_id': doc.id, 'checksum': doc.checksum,
        'checked_at': utcnow().isoformat(), 'status': 'unchanged',
        'evidence_urls': [str(doc.url)], 'relation_review': 'Reviewed only the named passages and date interval.',
        'verified_scope': [{'as_of_from': str(start or local_date()),
            'as_of_to': str(end or local_date()+timedelta(days=1)),
            'chunk_checksums': {doc.chunks[0].id: doc.chunks[0].checksum}}]}
    path = tmp_path/'receipt.json'; path.write_text(json.dumps(receipt))
    result = record_source_review(store, path)
    policy = {'version': 1, 'release_id': payload['id'], 'receipts': {doc.id: result['receipt_sha256']}}
    path = tmp_path/'gate.json'; path.write_text(json.dumps(policy))
    activate_source_gate(store, path)
    return policy, receipt


@pytest.mark.parametrize('snapshot', [False, True])
async def test_scoped_passage_answers_despite_unreviewed_corpus(store, settings, tmp_path, snapshot):
    good, other = document(), document('unreviewed')
    payload = release(store, [good, other])
    review(store, payload, other, 'changed')
    install_gate(store, payload, good, tmp_path)
    settings.allow_stale_generation = snapshot
    assert not store.source_fresh(payload)  # A partial review never blesses the corpus.
    result = await Agent(store, FakeProvider(settings)).run(
        ChatRequest(session_id='0'*36, message='Điều kiện bồi thường?'), noop)
    assert result.status == 'answered'
    assert {c.document_id for c in result.citations} == {good.id}
    assert result.source_context['source_fresh'] is True  # Cited passages only.


def test_reviewed_passage_is_not_crowded_out_by_unreviewed_lexical_noise(store, settings, tmp_path):
    noise = document('noise', text='bồi thường bồi thường bồi thường bồi thường thu hồi đất')
    good = document('good', text='Điều 1. Điều kiện bồi thường khi thu hồi đất ở.', locator='Điều 1')
    payload = release(store, [noise, good])
    install_gate(store, payload, good, tmp_path)
    hits = store.search('bồi thường thu hồi đất', None, None, payload['id'], None, local_date())
    assert hits and hits[0].document.id == 'good'


@pytest.mark.parametrize('snapshot', [False, True])
@pytest.mark.parametrize('violation', ['other_document', 'other_chunk', 'before', 'after',
                                      'changed', 'unavailable', 'expired', 'replaced_receipt', 'missing_receipt'])
async def test_scope_violations_always_veto_approved_claims(store, settings, tmp_path, snapshot, violation):
    doc, other = document(), document('other')
    doc.chunks.append(Chunk(id='not-reviewed', document_id=doc.id, locator='Điều 2',
                            text='Unreviewed public text.', checksum=digest('Unreviewed public text.')))
    payload = release(store, [doc, other])
    install_gate(store, payload, doc, tmp_path)
    as_of = local_date()
    chosen = doc
    if violation == 'other_document': chosen = other
    if violation == 'other_chunk': chosen = doc.model_copy(update={'chunks': [doc.chunks[1]]})
    if violation == 'before': as_of -= timedelta(days=1)
    if violation == 'after': as_of += timedelta(days=1)
    if violation in {'changed', 'unavailable'}: review(store, payload, doc, violation)
    if violation == 'replaced_receipt': review(store, payload, doc, 'unchanged')
    if violation == 'expired':
        # Age the pinned row while preserving canonical receipt integrity.
        row = store.rows('SELECT * FROM source_reviews')[0]
        value = json.loads(row['receipt']); value['checked_at'] = (utcnow()-timedelta(days=8)).isoformat()
        canonical = json.dumps(value, ensure_ascii=False, sort_keys=True)
        ident = hashlib.sha256(canonical.encode()).hexdigest()
        with store.transaction() as conn:
            store.execute(conn, 'UPDATE source_reviews SET id=?,checked_at=?,receipt=?',
                          (ident, value['checked_at'], canonical))
        gate = store.source_gate(payload['id']); gate['receipts'][doc.id] = ident
        store.set_state('source_gate:'+payload['id'], json.dumps(gate))
    if violation == 'missing_receipt':
        with store.transaction() as conn: store.execute(conn, 'DELETE FROM source_reviews')
    settings.allow_stale_generation = snapshot
    state = approved_state(payload, [chosen], as_of)
    await Agent(store, FakeProvider(settings)).finish(state)
    assert state['result'].status == 'insufficient_evidence'
    assert not state['result'].citations and not state['result'].verified_claims


@pytest.mark.parametrize('value', ['invalid', '{}', 'null', '{"version":1,"receipts":[]}'])
async def test_malformed_gate_is_fail_closed(store, settings, value):
    doc = document(); payload = release(store, [doc])
    store.set_state('source_gate:'+payload['id'], value)
    settings.allow_stale_generation = True
    state = approved_state(payload, [doc], local_date())
    await Agent(store, FakeProvider(settings)).finish(state)
    assert state['result'].status == 'insufficient_evidence'
    assert store.source_gate_status(payload)['usable'] is False


async def test_unreviewed_date_refuses_before_synthesis_without_model(store, settings, tmp_path):
    doc = document(); payload = release(store, [doc])
    install_gate(store, payload, doc, tmp_path)
    provider = FakeProvider(settings)
    async def forbidden(*args, **kwargs):
        pytest.fail('No model call is needed when every passage is outside reviewed scope')
    provider.generate = forbidden
    result = await Agent(store, provider).run(ChatRequest(session_id='0'*36,
        message='Điều kiện bồi thường?', as_of=local_date()+timedelta(days=1)), noop)
    assert result.status == 'insufficient_evidence' and not result.citations
    assert result.llm_calls == 0
    assert 'phạm vi đã xác minh' in result.content


def test_restore_keeps_gate_and_requires_receipt_reapplication(store, settings, tmp_path):
    doc = document(); payload = release(store, [doc]); install_gate(store, payload, doc, tmp_path)
    target = tmp_path/'backup.json'; store.backup(target)
    isolated = Store(settings.model_copy(update={'sqlite_path': str(tmp_path/'restore.db')}))
    try:
        isolated.restore(target)
        assert isolated.source_gate(payload['id']) == store.source_gate(payload['id'])
        assert isolated.source_gate_status(payload)['usable'] is False
        record_source_review(isolated, tmp_path/'receipt.json')
        assert isolated.source_gate_status(payload)['usable'] is True
    finally: isolated.close()


def test_status_and_startup_do_not_hide_reviewed_subset(store, settings, tmp_path):
    from landlaw.ops import status as ops_status
    doc = document(); payload = release(store, [doc, document('unreviewed')])
    install_gate(store, payload, doc, tmp_path)
    settings.allow_stale_generation = False
    with TestClient(create_app(settings, store, FakeProvider(settings))) as client:
        ready = client.get('/readyz').json()
        status = client.get('/api/v1/status').json()
    assert ready['source_gate']['policy_sha256'] == status['source_gate']['policy_sha256']
    assert len(ready['configuration_sha256']) == 64
    assert status['generation_available'] and not status['source_fresh']
    assert status['source_gate']['eligible_passages'] == 1
    assert ops_status(store)['needs_attention'] is False


def test_gate_status_counts_only_passages_valid_today(store, tmp_path):
    doc = document(); payload = release(store, [doc])
    install_gate(store, payload, doc, tmp_path,
                 start=local_date()-timedelta(days=2), end=local_date()-timedelta(days=1))
    status = store.source_gate_status(payload)
    assert status['eligible_passages'] == 0 and status['usable'] is False
    historical = store.source_gate_status(payload, as_of=local_date()-timedelta(days=2))
    assert historical['eligible_passages'] == 1 and historical['usable'] is True


def test_gate_status_reads_each_pinned_receipt_once(monkeypatch, store, tmp_path):
    doc = document(); payload = release(store, [doc])
    scopes = [{'as_of_from': str(local_date()-timedelta(days=offset)),
               'as_of_to': str(local_date()-timedelta(days=offset-1)),
               'chunk_checksums': {doc.chunks[0].id: doc.chunks[0].checksum}}
              for offset in range(3)]
    receipt = {'document_id': doc.id, 'checksum': doc.checksum,
        'checked_at': utcnow().isoformat(), 'status': 'unchanged',
        'evidence_urls': [str(doc.url)],
        'relation_review': 'Reviewed only the named passages and date intervals.',
        'verified_scope': scopes}
    path = tmp_path/'receipt.json'; path.write_text(json.dumps(receipt))
    pinned = record_source_review(store, path)
    policy = {'version': 1, 'release_id': payload['id'], 'receipts': {doc.id: pinned['receipt_sha256']}}
    path = tmp_path/'gate.json'; path.write_text(json.dumps(policy))
    activate_source_gate(store, path)

    original, calls = store.rows, []
    def counting(sql, params=()):
        if 'source_reviews' in sql:
            calls.append(sql)
        return original(sql, params)
    monkeypatch.setattr(store, 'rows', counting)
    status = store.source_gate_status(payload)
    assert status['eligible_passages'] == 1 and status['usable'] is True
    # One release-level receipt read serves every document and date window.
    assert len(calls) == 1, calls


@pytest.mark.parametrize('mutation', ['checksum', 'document', 'empty', 'dates'])
def test_receipt_import_rejects_invalid_scope(store, tmp_path, mutation):
    doc = document(); payload = release(store, [doc, document('other')])
    _, receipt = install_gate(store, payload, doc, tmp_path)
    scope = receipt['verified_scope'][0]
    if mutation == 'checksum': scope['chunk_checksums'][doc.chunks[0].id] = 'wrong'
    if mutation == 'document': scope['chunk_checksums'] = {'other-1': digest('irrelevant')}
    if mutation == 'empty': scope['chunk_checksums'] = {}
    if mutation == 'dates': scope['as_of_to'] = scope['as_of_from']
    path = tmp_path/'invalid.json'; path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError): record_source_review(store, path)


def test_receipt_accepts_only_snapshot_bound_official_cdn_attachment(store, tmp_path):
    from landlaw.models import SourceFile
    url = 'https://congbaocdn.chinhphu.vn/reviewed.pdf'
    doc = document().model_copy(update={'source_files': [SourceFile(url=url, checksum='a'*64,
        first_page_index=0, last_page_index=0)]})
    payload = release(store, [doc]); _, receipt = install_gate(store, payload, doc, tmp_path)
    receipt['evidence_urls'].append(url)
    path = tmp_path/'cdn.json'; path.write_text(json.dumps(receipt))
    assert record_source_review(store, path)['status'] == 'unchanged'
    receipt['evidence_urls'][-1] = 'https://congbaocdn.chinhphu.vn/unbound.pdf'
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='source evidence'):
        record_source_review(store, path)
