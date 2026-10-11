import asyncio
import json
import logging
import secrets
import time
import uuid
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .agent import Agent
from .evaluation import configuration_fingerprint
from .config import Settings, get_settings
from .models import ChatRequest, ChatResult, TraceEvent
from .provider import Gemini
from .security import digest, hash_ip, local_date, new_token, redact, utcnow
from .store import RateLimited, Store

logger = logging.getLogger("landlaw")


def create_app(settings: Settings | None = None, store: Store | None = None, provider=None):
    settings = settings or get_settings()
    state = {}

    @asynccontextmanager
    async def lifespan(app):
        state["store"] = store or Store(settings)
        state["provider"] = provider or Gemini(settings, state["store"])
        state["agent"] = Agent(state["store"], state["provider"])
        state["semaphore"] = asyncio.Semaphore(settings.max_concurrent_requests)
        state["ip_secret"] = settings.ip_hash_secret.get_secret_value() or secrets.token_hex(32)
        state["configuration"] = configuration_fingerprint(settings)
        yield
        if not provider:
            await state["provider"].close()
        if not store:
            state["store"].close()

    app = FastAPI(title="Hà Nội · Pháp luật đất đai", version="0.1.0", lifespan=lifespan,
                  docs_url="/docs" if settings.app_env != "production" else None, redoc_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_methods=["GET", "POST"],
                       allow_headers=["Authorization", "Content-Type"], expose_headers=["Retry-After", "X-Request-ID"])

    @app.middleware("http")
    async def metadata(request, call_next):
        request_id = str(uuid.uuid4())
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception:
            logger.error(json.dumps({"request_id": request_id, "event": "request_failed"}))
            response = JSONResponse({"detail": "Dịch vụ dữ liệu chưa sẵn sàng. Vui lòng thử lại.", "request_id": request_id}, status_code=503)
        response.headers.update({"X-Request-ID": request_id, "X-Content-Type-Options": "nosniff",
                                 "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"})
        logger.info(json.dumps({"request_id": request_id, "method": request.method, "status": response.status_code,
                                "elapsed_ms": int((time.monotonic()-started)*1000)}))
        return response

    def identity(request):
        ip = request.client.host if request.client else "unknown"
        # Enable only when the ingress guarantees it overwrites X-Forwarded-For.
        if settings.trust_proxy_headers:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                ip = forwarded.split(",")[-1].strip()
        return hash_ip(ip, state["ip_secret"])

    async def authenticated(request, session_id):
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer ") or not await asyncio.to_thread(state["store"].authenticate, session_id, auth[7:]):
            raise HTTPException(404, "Phiên không tồn tại hoặc không có quyền truy cập")

    async def reserve(limits):
        try:
            await asyncio.to_thread(state["store"].consume, limits)
        except RateLimited as exc:
            raise HTTPException(429, "Đã đạt giới hạn lượt dùng", headers={"Retry-After": str(exc.retry_after)})

    @app.get("/healthz")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    @app.get("/readyz")
    async def ready():
        try:
            await asyncio.to_thread(state["store"].ready)
            release = await asyncio.to_thread(state["store"].release, None, True)
        except Exception:
            return JSONResponse({"status": "not_ready", "database": False, "reason": "database_unavailable"}, status_code=503)
        configured = state["provider"].configured
        data = {"status": "ready" if configured and release else "not_ready", "database": True,
                "llm_configured": configured, "corpus_release": (release or {}).get("id"),
                "checked_at": (release or {}).get("checked_at"), "storage": "postgresql" if state["store"].postgres else "sqlite-development"}
        return JSONResponse(data, status_code=200 if configured and release else 503)

    @app.post("/api/v1/sessions", status_code=201)
    async def session(request: Request):
        now, ip = utcnow(), identity(request)
        await reserve([(f"session-create:{ip}:{now.strftime('%Y-%m-%dT%H:%M')}", 10, 60),
                       (f"session-create:{ip}:{now.date()}", 100, 86400)])
        session_id, token = str(uuid.uuid4()), new_token()
        await asyncio.to_thread(state["store"].create_session, session_id, token)
        return {"session_id": session_id, "token": token, "retention_days": settings.session_retention_days}

    @app.get("/api/v1/sessions/{session_id}/messages")
    async def messages(session_id: str, request: Request):
        await authenticated(request, session_id)
        return {"messages": await asyncio.to_thread(state["store"].messages, session_id, 50)}

    @app.get("/api/v1/sessions/{session_id}/traces/{trace_id}")
    async def trace(session_id: str, trace_id: str, request: Request):
        await authenticated(request, session_id)
        result = await asyncio.to_thread(state["store"].trace, trace_id, session_id)
        if result is None:
            raise HTTPException(404, "Không tìm thấy trace")
        return {"trace": result}

    @app.get("/api/v1/documents")
    async def documents():
        docs = await asyncio.to_thread(state["store"].documents)
        return {"documents": [d.model_dump(mode="json", exclude={"chunks"}) for d in docs]}

    @app.get("/api/v1/documents/{document_id}")
    async def document(document_id: str):
        doc = await asyncio.to_thread(state["store"].document, document_id)
        if not doc:
            raise HTTPException(404, "Tài liệu chưa được công bố")
        return {"document": doc.model_dump(mode="json"), "relations": [r.model_dump(mode="json")
                for r in await asyncio.to_thread(state["store"].relations, document_id)]}

    @app.get("/api/v1/projects")
    async def projects():
        path = settings.data_dir / "projects.json"
        return {"projects": json.loads(path.read_text()) if path.exists() else []}

    @app.get("/api/v1/evaluations/latest")
    async def evaluations():
        path = settings.reports_dir / "latest.json"
        if not path.exists():
            return {"status": "not_run", "message": "Chưa chạy benchmark với API và corpus thật.", "results": []}
        return json.loads(path.read_text())

    @app.post("/api/v1/chat")
    async def chat(body: ChatRequest, request: Request):
        await authenticated(request, body.session_id)
        now, ip = utcnow(), identity(request)
        await reserve([(f"minute:{kind}:{who}:{now.strftime('%Y-%m-%dT%H:%M')}", 3, 60)
                       for kind, who in [("session", body.session_id), ("ip", ip)]] +
                      [(f"daily:{kind}:{who}:{now.date()}", 20, 86400)
                       for kind, who in [("session", body.session_id), ("ip", ip)]])
        semaphore = state["semaphore"]
        if semaphore.locked():
            raise HTTPException(429, "Hai lượt hỏi đang được xử lý", headers={"Retry-After": "5"})
        await semaphore.acquire()

        async def stream():
            queue = asyncio.Queue(maxsize=50)

            async def emit(event):
                await queue.put(("progress", event.model_dump(mode="json")))

            async def work():
                try:
                    release_id = await asyncio.to_thread(state["store"].state, "active_release")
                    history = await asyncio.to_thread(state["store"].messages, body.session_id, 8)
                    cache_key = digest(json.dumps({"session": body.session_id, "question": body.message,
                        "history": history, "release": release_id, "model": settings.gemini_model,
                        "configuration": state["configuration"],
                        "embedding": settings.embedding_model, "as_of": str(body.as_of or local_date()),
                        "project": body.project, "mode": body.mode}, sort_keys=True, ensure_ascii=False))
                    cached = await asyncio.to_thread(state["store"].cached_answer, cache_key, body.session_id)
                    if cached and (body.as_of is None or body.as_of >= local_date()):
                        release = await asyncio.to_thread(state["store"].release, release_id, True)
                        checked = datetime.fromisoformat(release["checked_at"].replace("Z", "+00:00")) if release else None
                        if not checked or utcnow() - checked > timedelta(days=7):
                            cached = None
                    if cached:
                        result = ChatResult.model_validate(cached).model_copy(update={"trace_id": str(uuid.uuid4()),
                            "llm_calls": 0, "embedding_calls": 0, "tool_calls": 0, "token_usage": 0, "elapsed_ms": 0,
                            "trace": [TraceEvent(step="cache", summary="Đã dùng kết quả đã kiểm tra của cùng phiên và phạm vi câu hỏi.")]})
                    else:
                        result = await state["agent"].run(body, emit)
                        await asyncio.to_thread(state["store"].cache_answer, cache_key, body.session_id, result)
                    # A successful result is not delivered until durable storage succeeds.
                    await asyncio.to_thread(state["store"].save_turn, body.session_id, redact(body.message), result)
                    await queue.put(("result", result.model_dump(mode="json")))
                    logger.info(json.dumps({"event": "turn_finished", "trace_id": result.trace_id,
                        "status": result.status, "model": result.model, "llm_calls": result.llm_calls,
                        "tool_calls": result.tool_calls, "tokens": result.token_usage, "elapsed_ms": result.elapsed_ms}))
                except Exception:
                    await queue.put(("failure", {"status": "error", "content": "Dịch vụ dữ liệu chưa sẵn sàng; kết quả chưa được lưu."}))
                finally:
                    await queue.put(("done", {}))

            task = asyncio.create_task(work())
            try:
                yield ": connected\n\n"
                while True:
                    try:
                        event, payload = await asyncio.wait_for(queue.get(), timeout=10)
                    except TimeoutError:
                        yield ": heartbeat\n\n"
                        continue
                    if event == "done":
                        break
                    yield f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                semaphore.release()

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    return app


app = create_app()
