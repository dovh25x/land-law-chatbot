"""Source review regressions use only the isolated SQLite test store."""
import json
import uuid
from datetime import date, timedelta

import pytest

from conftest import document, release
from test_agent import FakeProvider, noop
from landlaw.agent import Agent, Plan, Verification
from landlaw.models import ChatRequest, Claim, Draft, Evidence
from landlaw.provider import Budget
from landlaw.security import local_date, utcnow


def review(store, payload, doc, status, checked_at=None, checksum=None):
    stamp = checked_at or utcnow().isoformat()
    receipt = dict(status=status, checked_at=stamp)
    with store.transaction() as conn:
        store.execute(conn, 'INSERT INTO source_reviews VALUES(?,?,?,?,?,?,?)', (
            str(uuid.uuid4()), payload['id'], doc.id, checksum or doc.checksum,
            stamp, status, json.dumps(receipt)))


def approved_state(payload, docs, as_of):
    from conftest import supplied_synthesis_fixture
    from landlaw.agent import SupportingQuote
    claims = [Claim(text='Thông tin có căn cứ về điều kiện bồi thường.',
                    citation_ids=[doc.chunks[0].id]) for doc in docs]
    return supplied_synthesis_fixture({'request': ChatRequest(session_id='0'*36, message='Điều kiện bồi thường?'),
            'budget': Budget(), 'release': payload, 'as_of': as_of, 'plan': Plan(),
            'evidence': [Evidence(document=doc, chunk=doc.chunks[0], applicability='current') for doc in docs],
            'draft': Draft(status='answered', claims=claims),
            'verification': Verification(supported_claim_indexes=list(range(len(claims))),
                supporting_quotes=[SupportingQuote(claim_index=i,citation_id=doc.chunks[0].id,
                    quote=doc.chunks[0].text[:1600]) for i,doc in enumerate(docs)]),
            'trace': [], 'emit': noop})


@pytest.mark.parametrize('receipt_status', ['changed', 'unavailable'])
@pytest.mark.parametrize('allow_snapshot', [False, True])
@pytest.mark.parametrize('historical', [False, True])
async def test_finish_rechecks_adverse_review_even_with_approved_claims(
        store, settings, receipt_status, allow_snapshot, historical):
    doc = document(); payload = release(store, [doc])
    review(store, payload, doc, receipt_status)
    settings.allow_stale_generation = allow_snapshot
    state = approved_state(payload, [doc], date(2024, 8, 2) if historical else local_date())
    await Agent(store, FakeProvider(settings)).finish(state)
    result = state['result']
    assert result.status == 'insufficient_evidence'
    assert not result.verified_claims and not result.citations
    assert state['draft'].claims[0].text not in result.content
    assert not result.answer_sections and result.support_level == 'insufficient'


@pytest.mark.parametrize('receipt_status', ['changed', 'unavailable'])
async def test_verify_never_delegates_adverse_source_approval_to_model(store, settings, receipt_status):
    doc = document(); payload = release(store, [doc])
    review(store, payload, doc, receipt_status)
    settings.allow_stale_generation = True
    state = approved_state(payload, [doc], local_date())
    agent = Agent(store, FakeProvider(settings))
    await agent.verify(state)
    assert not state['verification'].supported_claim_indexes
    assert state['verification'].issues
    assert state['budget'].llm_calls == 0


async def test_finish_catches_source_change_after_verification_and_vetoes_whole_group(store, settings):
    docs = [document(), document('other')]; payload = release(store, docs)
    state = approved_state(payload, docs, local_date())
    agent = Agent(store, FakeProvider(settings, verification=Verification(supported_claim_indexes=[0, 1])))
    await agent.verify(state)
    assert state['verification'].supported_claim_indexes == [0, 1]
    review(store, payload, docs[1], 'changed')
    settings.allow_stale_generation = True
    await agent.finish(state)
    assert not state['result'].verified_claims and not state['result'].citations
    assert state['result'].status == 'insufficient_evidence'


async def test_changed_uncited_document_does_not_veto_reviewed_cited_source(store, settings):
    good, changed = document(), document('other')
    payload = release(store, [good, changed]); review(store, payload, changed, 'changed')
    settings.allow_stale_generation = True
    state = approved_state(payload, [good], local_date())
    agent = Agent(store, FakeProvider(settings))
    await agent.verify(state); await agent.finish(state)
    assert state['result'].status == 'answered'
    assert {c.document_id for c in state['result'].citations} == {good.id}


@pytest.mark.parametrize('allow_snapshot,historical,expected', [
    (False, False, 'insufficient_evidence'), (True, False, 'answered'),
    (False, True, 'answered'), (True, True, 'answered'),
])
async def test_stale_review_retains_explicit_snapshot_and_historical_behavior(
        store, settings, allow_snapshot, historical, expected):
    doc = document(); payload = release(store, [doc])
    payload['checked_at'] = (utcnow()-timedelta(days=8)).isoformat()
    settings.allow_stale_generation = allow_snapshot
    state = approved_state(payload, [doc], date(2024, 8, 2) if historical else local_date())
    await Agent(store, FakeProvider(settings)).finish(state)
    assert state['result'].status == expected
    assert state['result'].source_context['source_fresh'] is False


@pytest.mark.parametrize('status,age,expected', [
    (None, 0, 'fresh'), (None, 8, 'stale'),
    ('unchanged', 0, 'fresh'), ('unchanged', 8, 'stale'),
    ('changed', 0, 'changed'), ('changed', 8, 'changed'),
    ('unavailable', 0, 'unknown'), ('unavailable', 8, 'unknown'),
    ('unexpected', 0, 'unknown'),
])
def test_source_review_states_do_not_confuse_age_and_known_changes(store, status, age, expected):
    doc = document(); payload = release(store, [doc])
    stamp = (utcnow()-timedelta(days=age)).isoformat()
    if status is None:
        payload['checked_at'] = stamp
    else:
        review(store, payload, doc, status, checked_at=stamp)
    assert store.source_review_states(payload) == {doc.id: expected}
    assert store.source_fresh(payload) is (expected == 'fresh')


@pytest.mark.parametrize('stamp', [None, '', 'invalid', '2026-01-01T12:00:00',
                                    (utcnow()+timedelta(days=1)).isoformat()])
def test_missing_invalid_or_future_review_time_is_unknown(store, stamp):
    doc = document(); payload = release(store, [doc])
    payload['checked_at'] = stamp
    assert store.source_review_states(payload) == {doc.id: 'unknown'}
    assert not store.source_fresh(payload)


def test_review_is_bound_to_checksum_and_latest_receipt(store):
    doc = document(); payload = release(store, [doc]); now = utcnow()
    review(store, payload, doc, 'changed', (now-timedelta(seconds=2)).isoformat())
    review(store, payload, doc, 'unchanged', (now-timedelta(seconds=1)).isoformat(), checksum='other-version')
    assert store.source_review_states(payload) == {doc.id: 'changed'}
    review(store, payload, doc, 'unchanged', now.isoformat())
    assert store.source_review_states(payload) == {doc.id: 'fresh'}


def test_source_review_states_read_the_release_once(monkeypatch, store):
    docs = [document(), document('other')]; payload = release(store, docs)
    review(store, payload, docs[0], 'unchanged')
    review(store, payload, docs[1], 'changed')
    original, calls = store.rows, []
    def counting(sql, params=()):
        if 'source_reviews' in sql:
            calls.append(sql)
        return original(sql, params)
    monkeypatch.setattr(store, 'rows', counting)
    assert store.source_review_states(payload) == {docs[0].id: 'fresh', docs[1].id: 'changed'}
    assert len(calls) == 1, calls


def test_unknown_selected_document_is_not_silently_ignored(store):
    doc = document(); payload = release(store, [doc])
    assert store.source_review_states(payload, {doc.id, 'missing'}) == {doc.id: 'fresh', 'missing': 'unknown'}
    assert not store.source_fresh(payload, {doc.id, 'missing'})
    assert not store.source_fresh({})
    assert not store.source_fresh(payload, set())


@pytest.mark.parametrize('receipt_status', ['changed', 'unavailable'])
async def test_unknown_or_changed_source_cannot_publish_through_full_graph(store, settings, receipt_status):
    doc = document(); payload = release(store, [doc]); review(store, payload, doc, receipt_status)
    settings.allow_stale_generation = True
    result = await Agent(store, FakeProvider(settings)).run(
        ChatRequest(session_id='0'*36, message='Điều kiện bồi thường?'), noop)
    assert result.status == 'insufficient_evidence'
    assert not result.verified_claims and not result.citations
    assert result.llm_calls <= 6 and result.tool_calls <= 12
