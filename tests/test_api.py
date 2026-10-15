import json

from fastapi.testclient import TestClient

from landlaw.api import create_app
from conftest import release
from test_agent import FakeProvider


def test_auth_sse_session_history_and_trace_isolation(settings, store):
    release(store)
    with TestClient(create_app(settings, store, FakeProvider(settings))) as client:
        first = client.post("/api/v1/sessions").json()
        second = client.post("/api/v1/sessions").json()
        headers = {"Authorization": f"Bearer {first['token']}"}
        assert client.get(f"/api/v1/sessions/{first['session_id']}/messages").status_code == 404
        response = client.post("/api/v1/chat", headers=headers, json={"session_id": first["session_id"], "message": "bồi thường thu hồi đất"})
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        frames = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        result = next(f for f in frames if "trace_id" in f)
        assert result["status"] == "answered"
        assert response.text.index('"step": "verification"') < response.text.index('"status": "answered"')
        history = client.get(f"/api/v1/sessions/{first['session_id']}/messages", headers=headers).json()
        assert len(history["messages"]) == 2
        other_headers = {"Authorization": f"Bearer {second['token']}"}
        assert client.get(f"/api/v1/sessions/{first['session_id']}/messages", headers=other_headers).status_code == 404
        assert client.get(f"/api/v1/sessions/{second['session_id']}/traces/{result['trace_id']}", headers=other_headers).status_code == 404


def test_rate_limit_and_retry_after(settings, store):
    release(store)
    with TestClient(create_app(settings, store, FakeProvider(settings))) as client:
        session = client.post("/api/v1/sessions").json()
        for _ in range(3):
            assert client.post("/api/v1/chat", headers={"Authorization": f"Bearer {session['token']}"},
                               json={"session_id": session["session_id"], "message": "bồi thường"}).status_code == 200
        response = client.post("/api/v1/chat", headers={"Authorization": f"Bearer {session['token']}"},
                               json={"session_id": session["session_id"], "message": "bồi thường"})
        assert response.status_code == 429 and response.headers["retry-after"] == "60"


def test_readiness_without_key_does_not_fake_success(settings, store):
    settings.gemini_api_key = type(settings.gemini_api_key)("")
    with TestClient(create_app(settings, store)) as client:
        assert client.get("/healthz").status_code == 200
        ready = client.get("/readyz")
        assert ready.status_code == 503 and not ready.json()["llm_configured"]


def test_evaluation_for_another_model_does_not_certify_current_app(settings,store):
    payload=release(store)
    settings.reports_dir.mkdir(parents=True,exist_ok=True)
    report={'status':'reviewed','release':payload['id'],'configuration_sha256':'previous-model-config',
            'acceptance_passed':True,'results':[]}
    (settings.reports_dir/'latest.json').write_text(json.dumps(report))
    (settings.reports_dir/'smoke.json').write_text(json.dumps(report))
    with TestClient(create_app(settings,store,FakeProvider(settings))) as client:
        result=client.get('/api/v1/evaluations/latest').json()
        assert result['matches_active_release']
        assert not result['matches_active_configuration']
        assert not result['smoke_matches_active_configuration']
        assert not result['acceptance_valid_for_active']


def test_database_outage_readiness_is_sanitized(settings,store,monkeypatch):
    def fail():raise RuntimeError('private database credentials must not be returned')
    monkeypatch.setattr(store,'ready',fail)
    with TestClient(create_app(settings,store,FakeProvider(settings))) as client:
        response=client.get('/readyz')
        assert response.status_code==503 and response.json()['reason']=='database_unavailable'
        assert 'credentials' not in response.text


def test_failed_durable_save_never_streams_success(settings,store,monkeypatch):
    release(store)
    def fail(*args):raise RuntimeError('private database credentials must not be returned')
    monkeypatch.setattr(store,'save_turn',fail)
    with TestClient(create_app(settings,store,FakeProvider(settings))) as client:
        sid=client.post('/api/v1/sessions').json()
        response=client.post('/api/v1/chat',headers={'Authorization':'Bearer '+sid['token']},
                             json={'session_id':sid['session_id'],'message':'bồi thường thu hồi đất'})
        assert 'event: failure' in response.text and 'event: result' not in response.text
        assert 'credentials' not in response.text


def test_chat_pins_release_when_publication_changes_during_request(settings,store,monkeypatch):
    from conftest import document
    old=release(store,release_id='old')
    staged={**old,'id':'new','documents':[document('new-law').model_dump(mode='json')]}
    store.stage(staged)
    original=store.messages
    switched=[]
    def switch(*args):
        if not switched:
            store.publish('new');switched.append(True)
        return original(*args)
    monkeypatch.setattr(store,'messages',switch)
    with TestClient(create_app(settings,store,FakeProvider(settings))) as client:
        sid=client.post('/api/v1/sessions').json()
        response=client.post('/api/v1/chat',headers={'Authorization':'Bearer '+sid['token']},
                             json={'session_id':sid['session_id'],'message':'bồi thường thu hồi đất'})
        frames=[json.loads(l[6:]) for l in response.text.splitlines() if l.startswith('data: ')]
        result=next(f for f in frames if 'trace_id' in f)
        assert result['status']=='answered' and result['corpus_release']=='old'
        assert store.state('active_release')=='new'


def test_demo_shared_proxy_daily_counter_does_not_lock_out_a_new_session(settings, store):
    from landlaw.security import hash_ip, utcnow
    day = utcnow().date()
    legacy = f"daily:ip:{hash_ip('testclient', settings.ip_hash_secret.get_secret_value())}:{day}"
    store.consume([(legacy, 20, 86400)] * 20)
    release(store)
    with TestClient(create_app(settings, store, FakeProvider(settings))) as client:
        session = client.post('/api/v1/sessions').json()
        response = client.post('/api/v1/chat', headers={'Authorization':'Bearer '+session['token']},
            json={'session_id':session['session_id'], 'message':'Bồi thường thu hồi đất'})
        assert response.status_code == 200
        assert store.rows('SELECT value FROM counters WHERE key=?', (legacy,))[0]['value'] == 20
        key = f"daily:session:{session['session_id']}:{day}"
        assert store.rows('SELECT value FROM counters WHERE key=?', (key,))[0]['value'] == 1


def test_demo_preserves_daily_session_limit_and_shared_ip_burst_limit(settings, store):
    from landlaw.security import utcnow
    release(store)
    with TestClient(create_app(settings, store, FakeProvider(settings))) as client:
        sessions = [client.post('/api/v1/sessions').json() for _ in range(3)]
        exhausted = sessions[0]
        key = f"daily:session:{exhausted['session_id']}:{utcnow().date()}"
        store.consume([(key, 20, 86400)] * 20)
        def chat(session):
            return client.post('/api/v1/chat', headers={'Authorization':'Bearer '+session['token']},
                json={'session_id':session['session_id'], 'message':'Bồi thường thu hồi đất'})
        assert chat(exhausted).status_code == 429
        assert chat(sessions[1]).status_code == 200
        assert chat(sessions[1]).status_code == 200
        assert chat(sessions[2]).status_code == 200
        response = chat(sessions[2])
        assert response.status_code == 429 and response.headers['retry-after'] == '60'
