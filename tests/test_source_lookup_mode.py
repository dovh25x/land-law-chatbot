"""Verified-only library uses the existing source gate, never generation."""
import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from conftest import document, release, session
from landlaw.api import create_app
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.models import Chunk
from landlaw.security import digest, local_date, utcnow
from test_scoped_source_gate import install_gate
from test_source_review_policy import review


class NeverGenerate:
    configured = False

    def __init__(self, settings):
        self.settings = settings
        self.calls = 0

    async def generate(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError('Source lookup must not call the model')


def setup_lookup(store, settings, tmp_path, *, start=None, end=None):
    good = document()
    good.chunks.append(Chunk(id='private-unreviewed', document_id=good.id, locator='Điều 2',
                             text='UNREVIEWED_SENTINEL', checksum=digest('UNREVIEWED_SENTINEL')))
    other = document('other', text='UNREVIEWED_OTHER_DOCUMENT')
    payload = release(store, [good, other])
    install_gate(store, payload, good, tmp_path, start=start, end=end)
    configured = settings.model_copy(update={'generation_enabled': False, 'source_lookup_only': True,
                                              'groq_api_key': ''})
    return good, payload, configured, NeverGenerate(configured)


def test_lookup_requires_generation_disabled_and_distinct_fingerprint(settings):
    assert settings.source_lookup_only is False
    with pytest.raises(ValidationError, match='SOURCE_LOOKUP_ONLY'):
        Settings(_env_file=None, database_url='', admin_database_url='', source_lookup_only=True,
                 generation_enabled=True)
    configured = settings.model_copy(update={'generation_enabled': False, 'source_lookup_only': True})
    assert configuration_fingerprint(configured) != configuration_fingerprint(settings)


def test_only_exact_reviewed_passages_are_exposed_without_bulk_read(store, settings, tmp_path, monkeypatch):
    doc, payload, configured, provider = setup_lookup(store, settings, tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError('Do not load unfiltered documents/open_document in lookup mode')
    monkeypatch.setattr(store, 'documents', forbidden)
    monkeypatch.setattr(store, 'open_document', forbidden)
    with TestClient(create_app(configured, store, provider)) as client:
        listed = client.get('/api/v1/documents')
        assert listed.status_code == 200
        body = listed.json()
        assert body['source_lookup_only'] and body['as_of'] == str(local_date())
        assert body['verified_passage_count'] == 1 and body['references'] == []
        assert [d['id'] for d in body['documents']] == [doc.id]
        assert body['documents'][0]['applicability_verified'] is False
        assert body['documents'][0]['whole_document_verified'] is False
        assert 'chunks' not in body['documents'][0]
        detail = client.get('/api/v1/documents/'+doc.id).json()
        assert detail['relations'] == []
        assert detail['document']['chunks'] == [doc.chunks[0].model_dump(mode='json')]
        assert 'UNREVIEWED' not in listed.text + json.dumps(detail)
        assert client.get('/api/v1/documents/other').status_code == 404
        assert client.get('/api/v1/documents/'+doc.id+'?locator=Điều%202').status_code == 404
    assert provider.calls == 0


@pytest.mark.parametrize('violation', ['changed', 'unavailable', 'missing', 'stale', 'unknown_policy',
                                      'text_changed', 'checksum_changed'])
def test_lookup_never_leaks_unreviewed_or_changed_excerpts(store, settings, tmp_path, violation):
    doc, payload, configured, provider = setup_lookup(store, settings, tmp_path)
    if violation in {'changed', 'unavailable'}:
        review(store, payload, doc, violation)
    elif violation == 'unknown_policy':
        store.set_state('source_gate:'+payload['id'], '{"invalid":true}')
    else:
        with store.transaction() as conn:
            if violation == 'missing':
                store.execute(conn, 'DELETE FROM source_reviews')
            elif violation == 'stale':
                store.execute(conn, 'UPDATE source_reviews SET checked_at=?',
                              ((utcnow()-timedelta(days=8)).isoformat(),))
            elif violation == 'text_changed':
                store.execute(conn, 'UPDATE chunks SET text=? WHERE id=?', ('TAMPERED_SENTINEL', doc.chunks[0].id))
            elif violation == 'checksum_changed':
                store.execute(conn, 'UPDATE chunks SET checksum=? WHERE id=?', (digest('tampered'), doc.chunks[0].id))
    with TestClient(create_app(configured, store, provider)) as client:
        result = client.get('/api/v1/documents')
        assert result.json()['documents'] == []
        assert result.json()['verified_passage_count'] == 0
        assert client.get('/api/v1/documents/'+doc.id).status_code == 404
        assert doc.chunks[0].text not in result.text and 'TAMPERED' not in result.text
    assert provider.calls == 0


def test_dates_are_exact_and_history_does_not_bless_current_day(store, settings, tmp_path):
    today = local_date()
    doc, payload, configured, provider = setup_lookup(store, settings, tmp_path,
        start=today-timedelta(days=1), end=today)
    with TestClient(create_app(configured, store, provider)) as client:
        assert client.get('/api/v1/documents').json()['documents'] == []
        path = '/api/v1/documents?as_of='+str(today-timedelta(days=1))
        assert client.get(path).json()['verified_passage_count'] == 1
        assert client.get('/api/v1/documents/'+doc.id+'?as_of='+str(today-timedelta(days=1))).status_code == 200
        assert client.get('/api/v1/documents?as_of=not-a-date').status_code == 422
    assert provider.calls == 0


def test_explicit_longer_review_interval_is_preserved(store, settings, tmp_path):
    today = local_date()
    doc, payload, configured, provider = setup_lookup(store, settings, tmp_path,
        start=today, end=today+timedelta(days=4))
    with TestClient(create_app(configured, store, provider)) as client:
        assert client.get('/api/v1/documents?as_of='+str(today+timedelta(days=2))).json()['verified_passage_count'] == 1
        assert client.get('/api/v1/documents?as_of='+str(today+timedelta(days=4))).json()['documents'] == []


def test_lookup_ready_without_llm_and_chat_hard_disabled_even_for_mutated_settings(store, settings, tmp_path):
    doc, payload, configured, provider = setup_lookup(store, settings, tmp_path)
    # model_copy/assignment bypasses validation: the API must still veto generation.
    configured.generation_enabled = True
    sid, token = session(store)
    with TestClient(create_app(configured, store, provider)) as client:
        status = client.get('/api/v1/status').json()
        assert status['source_lookup_only'] and not status['generation_available']
        assert not status['capabilities']['citizen_answers']
        assert client.get('/readyz').status_code == 200
        response = client.post('/api/v1/chat', headers={'Authorization': 'Bearer '+token},
                               json={'session_id': sid, 'message': 'Giải thích bồi thường'})
        assert response.status_code == 503
        assert response.json()['detail']['code'] == 'generation_disabled'
    assert provider.calls == 0


def test_normal_library_retains_existing_snapshot_behavior(store, settings):
    doc = document()
    release(store, [doc])
    provider = NeverGenerate(settings)
    with TestClient(create_app(settings, store, provider)) as client:
        assert client.get('/api/v1/documents').json()['documents'][0]['id'] == doc.id
        assert client.get('/api/v1/documents/'+doc.id).json()['document']['chunks'][0]['text'] == doc.chunks[0].text
    assert provider.calls == 0
