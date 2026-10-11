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
