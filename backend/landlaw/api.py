import asyncio
import json
import logging
import secrets
import time
import uuid
import hashlib
import hmac
import sys
import httpx
from datetime import date, datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .agent import Agent
from .evaluation import configuration_fingerprint
from .config import Settings, get_settings
from .models import ChatRequest, ChatResult, TraceEvent
from .provider import GroqProvider
from .security import digest, hash_ip, local_date, new_token, redact, utcnow
from .store import RateLimited, Store
from .publication import public_status

logger = logging.getLogger("landlaw")
if not logger.handlers:
    logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.INFO)
logger.propagate=False


def create_app(settings: Settings | None = None, store: Store | None = None, provider=None):
    settings = settings or get_settings()
    state = {}

    @asynccontextmanager
    async def lifespan(app):
        state["store"] = store or Store(settings)
        state["provider"] = provider or GroqProvider(settings, state["store"], usage_scope="public")
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
        request.state.request_id=request_id
        started = time.monotonic()
        request.state.started=started
        request.state.client_ip=request.client.host if request.client else 'unknown'
        if request.url.path.startswith('/api/'):
            body=bytearray()
            try:
                async with asyncio.timeout(10):
                    async for part in request.stream():
                        body.extend(part)
                        if len(body)>65536:
                            return JSONResponse({'detail':{'code':'body_too_large'}},status_code=413)
            except TimeoutError:
                return JSONResponse({'detail':{'code':'body_timeout'}},status_code=408)
            request._body=bytes(body)
            if settings.app_env=='production':
                stamp=request.headers.get('x-landlaw-time','')
                ip=request.headers.get('x-landlaw-ip','')
                signature=request.headers.get('x-landlaw-signature','')
                canonical='\n'.join((request.method,request.url.path,request.url.query,stamp,ip,hashlib.sha256(body).hexdigest()))
                expected=hmac.new(settings.ingress_secret.get_secret_value().encode(),canonical.encode(),hashlib.sha256).hexdigest()
                try:valid=abs(time.time()-int(stamp))<=60
                except ValueError:valid=False
                if not settings.ingress_secret.get_secret_value() or not valid or not ip or not hmac.compare_digest(expected,signature):
                    return JSONResponse({'detail':{'code':'untrusted_ingress'}},status_code=403)
                request.state.client_ip=ip
        try:
            async with asyncio.timeout(max(0.1,settings.turn_timeout_seconds-(time.monotonic()-started))):
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
        ip = request.state.client_ip
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

    def reviewed_documents(as_of, document_id=None, locator=None):
        """Expose exact reviewed excerpts, never load the whole embedded corpus.

        Receipt IDs only nominate candidates. The existing scoped gate still
        checks latest review, pinned receipt, checksum, freshness and date.
        """
        repo = state['store']
        release = repo.release(None, True)
        policy = repo.source_gate((release or {}).get('id')) or {}
        if policy.get('version') != 1:
            return []
        passages = {}
        try:
            for ident, receipt_id in policy['receipts'].items():
                if document_id and ident != document_id:
                    continue
                rows = repo.rows('SELECT receipt FROM source_reviews WHERE id=? AND release_id=? AND document_id=?',
                                 (receipt_id, release['id'], ident))
                for row in rows:
                    for scope in json.loads(row['receipt']).get('verified_scope', []):
                        if date.fromisoformat(scope['as_of_from']) <= as_of < date.fromisoformat(scope['as_of_to']):
                            for cid, checksum in scope['chunk_checksums'].items():
                                passages[(ident, cid, checksum)] = None
                                if len(passages) > 256:
                                    return []  # Bounded public read; malformed/oversized policy fails closed.
        except (ValueError, TypeError, KeyError, AttributeError):
            return []
        reviews = repo.scoped_source_reviews(release, list(passages), as_of)
        grouped = {}
        for ident, cid, checksum in passages:
            if reviews.get(ident+':'+cid) != 'fresh':
                continue
            chunk = repo.chunk(cid, release['id'])
            if (not chunk or chunk.document_id != ident or chunk.checksum != checksum
                    or digest(chunk.text) != checksum or (locator and chunk.locator != locator)):
                continue
            grouped.setdefault(ident, []).append(chunk.model_dump(mode='json'))
        result = []
        for doc in (release or {}).get('documents', []):
            if doc['id'] not in grouped:
                continue
            result.append({**doc, 'chunks': grouped[doc['id']], 'applicability_verified': False,
                'source_review_notes': 'Chỉ các đoạn hiển thị được review trong phạm vi ngày đã chọn; không xác minh toàn văn hoặc quyền lợi cá nhân.',
                'source_lookup_only': True, 'review_as_of': str(as_of),
                'verified_passage_count': len(grouped[doc['id']]), 'whole_document_verified': False})
        return result

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
        ready = bool(release) and (configured or settings.source_lookup_only)
        data = {"status": "ready" if ready else "not_ready", "database": True,
                "llm_configured": configured, "corpus_release": (release or {}).get("id"),
                "checked_at": (release or {}).get("checked_at"), "storage": "postgresql" if state["store"].postgres else "sqlite-development"}
        publication = await asyncio.to_thread(state['store'].publication)
        data.update(public_status(release, publication))
        data['configuration_sha256'] = state['configuration']
        data['source_gate'] = await asyncio.to_thread(state['store'].source_gate_status, release)
        data['source_lookup_only'] = settings.source_lookup_only
        return JSONResponse(data, status_code=200 if ready else 503)

    @app.post("/api/v1/sessions", status_code=201)
    async def session(request: Request):
        now, ip = utcnow(), identity(request)
        await reserve([(f"session-create:{ip}:{now.strftime('%Y-%m-%dT%H:%M')}", 10, 60),
                       (f"session-create:{ip}:{now.date()}", 100, 86400)])
        if settings.app_env=='production':
            payload=await request.json() if await request.body() else {}
            token=payload.get('turnstile_token')
            if not token or not settings.turnstile_secret_key.get_secret_value():
                raise HTTPException(400, {'code':'challenge_required'})
            try:
                async with httpx.AsyncClient(timeout=8) as client:
                    response=await client.post('https://challenges.cloudflare.com/turnstile/v0/siteverify',
                        data={'secret':settings.turnstile_secret_key.get_secret_value(),'response':token,
                              'remoteip':request.state.client_ip})
                    response.raise_for_status()
                    checked=response.json()
            except (httpx.HTTPError,ValueError):
                raise HTTPException(503, {'code':'challenge_unavailable'}) from None
            if not checked.get('success') or checked.get('hostname')!=settings.public_hostname or checked.get('action')!='create_session':
                raise HTTPException(400, {'code':'challenge_failed'})
        session_id, token = str(uuid.uuid4()), new_token()
        await asyncio.to_thread(state["store"].create_session, session_id, token)
        return {"session_id": session_id, "token": token, "retention_days": settings.session_retention_days}

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({'detail':{'code':'invalid_request','errors':[
            {'loc':list(e['loc']),'type':e['type']} for e in exc.errors()]}},status_code=422)

    @app.get('/api/v1/sessions/{session_id}')
    async def session_status(session_id: str, request: Request):
        await authenticated(request, session_id)
        return {'valid':True}

    @app.get('/api/v1/sessions/{session_id}/messages')
    @app.get('/api/v1/sessions/{session_id}/traces/{trace_id}')
    async def retired_history(session_id: str, trace_id: str | None=None):
        raise HTTPException(410, {'code':'browser_history_only'})

    @app.get('/api/v1/status')
    async def status():
        release=await asyncio.to_thread(state['store'].release,None,True)
        fresh=bool(release) and await asyncio.to_thread(state['store'].source_fresh,release)
        gate=await asyncio.to_thread(state['store'].source_gate_status,release)
        delay=await asyncio.to_thread(state['store'].cooldown)
        sources_available=gate['usable'] if gate is not None else (fresh or settings.allow_stale_generation)
        enabled=bool(release) and settings.generation_enabled and not settings.source_lookup_only and sources_available and not delay
        return {'generation_available':enabled,'reason':'disabled' if not settings.generation_enabled else
            'source_stale' if not sources_available or not release else 'provider_limited' if delay else None,
            'retry_after':delay or None,'corpus_release':(release or {}).get('id'), 'api_version':3,
            'capabilities':{'citizen_answers':not settings.source_lookup_only,'answer_schema_version':2},
            'source_lookup_only':settings.source_lookup_only,'source_lookup_as_of':str(local_date()),
            'source_fresh':fresh,'warning':None if fresh else 'source_stale',
            'source_gate':gate,
            'source_checked_at':(release or {}).get('checked_at')}

    @app.get("/api/v1/documents")
    async def documents(as_of: date | None = None):
        if settings.source_lookup_only:
            reviewed = await asyncio.to_thread(reviewed_documents, as_of or local_date())
            return {'documents': [{k:v for k,v in doc.items() if k != 'chunks'} for doc in reviewed],
                    'references': [], 'source_lookup_only': True, 'as_of': str(as_of or local_date()),
                    'verified_passage_count': sum(doc['verified_passage_count'] for doc in reviewed),
                    'whole_corpus_verified': False}
        docs = await asyncio.to_thread(state["store"].documents)
        from .catalog import references
        extra = await asyncio.to_thread(references, settings, {d.id for d in docs})
        return {"documents": [d.model_dump(mode="json", exclude={"chunks"}) for d in docs], 'references': extra}

    @app.get("/api/v1/documents/{document_id}")
    async def document(document_id: str, locator: str | None = Query(default=None,max_length=200), as_of: date | None = None):
        if settings.source_lookup_only:
            reviewed = await asyncio.to_thread(reviewed_documents, as_of or local_date(), document_id, locator)
            if not reviewed:
                raise HTTPException(404, 'Chưa có đoạn nguồn được xác minh cho văn bản và thời điểm này')
            return {'document': reviewed[0], 'relations': [], 'source_lookup_only': True,
                    'as_of': str(as_of or local_date()), 'whole_document_verified': False}
        doc = await asyncio.to_thread(state["store"].open_document, document_id, None, locator)
        if not doc:
            from .catalog import references
            indexed = await asyncio.to_thread(state['store'].documents)
            extra = await asyncio.to_thread(references, settings, {d.id for d in indexed})
            reference = next((item for item in extra if item['id'] == document_id), None)
            if reference:
                return {'document': reference, 'relations': []}
            raise HTTPException(404, "Tài liệu chưa được công bố")
        return {"document": doc.model_dump(mode="json"), "relations": [r.model_dump(mode="json")
                for r in await asyncio.to_thread(state["store"].relations, document_id)]}

    @app.get("/api/v1/projects")
    async def projects():
        path = settings.data_dir / "projects.json"
        return {"projects": [p for p in json.loads(path.read_text()) if p["id"] == "ring4"] if path.exists() else []}

    @app.get("/api/v1/evaluations/latest")
    async def evaluations():
        path = settings.reports_dir / "latest.json"
        active = await asyncio.to_thread(state['store'].state, 'active_release')
        report = json.loads(path.read_text()) if path.exists() else {"status": "not_run", "results": []}
        archive_path = settings.reports_dir / 'public-evaluations.json'
        archive = json.loads(archive_path.read_text()) if archive_path.exists() else {}
        runs = [{**run, 'matches_active_release': bool(active and run.get('release') == active),
                 'matches_active_configuration': run.get('configuration_sha256') == state['configuration']}
                for run in archive.get('runs', [])]
        preferred = next((r for r in runs if r['matches_active_release'] and r['matches_active_configuration'] and r.get('complete')), None)
        preferred = preferred or next((r for r in runs if r['matches_active_release'] and r.get('complete')), None)
        preferred = preferred or next((r for r in runs if r['matches_active_release']), None) or next(iter(runs), None)
        return {**report, **archive, 'runs': runs, 'default_run_id': preferred['id'] if preferred else None,
                'evaluation_release':report.get('release'), 'active_release':active,
                'active_configuration_sha256':state['configuration'],
                'matches_active_configuration':report.get('configuration_sha256')==state['configuration'],
                'matches_active_release':bool(active and active==report.get('release'))}

    @app.post('/api/v1/chat')
    async def chat(body: ChatRequest, request: Request):
        await authenticated(request, body.session_id)
        if settings.app_env=='production' and 'request_id' not in body.model_fields_set:
            raise HTTPException(426, {'code':'client_upgrade_required'})
        if settings.source_lookup_only or not settings.generation_enabled:
            raise HTTPException(503, {'code':'generation_disabled'})
        now, ip = utcnow(), identity(request)
        await reserve([(f"minute:{kind}:{who}:{now.strftime('%Y-%m-%dT%H:%M')}", 3, 60)
                       for kind, who in [('session', body.session_id), ('ip', ip)]]+
                      [(f'daily:session:{body.session_id}:{now.date()}',20,86400)])
        semaphore=state['semaphore']
        if semaphore.locked():
            raise HTTPException(429, {'code':'system_busy'},headers={'Retry-After':'5'})
        await semaphore.acquire()
        turn_id=str(body.request_id)
        canonical=body.model_dump_json()
        fingerprint=hmac.new(state['ip_secret'].encode(),canonical.encode(),hashlib.sha256).hexdigest()
        try:
            conflict=await asyncio.to_thread(state['store'].start_turn,turn_id,body.session_id,fingerprint)
            if conflict:
                raise HTTPException(409, {'code':conflict,'replay_available':False})
        except BaseException:
            semaphore.release()
            raise

        async def stream():
            queue=asyncio.Queue()
            async def emit(event):
                queue.put_nowait(('progress',event.model_dump(mode='json')))
            async def work():
                outcome='error'
                try:
                    remaining=max(.01,settings.turn_timeout_seconds-(time.monotonic()-request.state.started))
                    async with asyncio.timeout(remaining):
                        release_id=await asyncio.to_thread(state['store'].state,'active_release')
                        result=await state['agent'].run(body,emit,release_id)
                        # Only metadata is durable. No replayable answer is stored.
                        await asyncio.to_thread(state['store'].finish_turn,turn_id,'completed')
                        outcome='completed'
                        queue.put_nowait(('result',result.model_dump(mode='json')))
                        logger.info(json.dumps({'event':'turn_finished','request_id':request.state.request_id,
                            'trace_id':result.trace_id,'status':result.status,'model':result.model,
                            'llm_calls':result.llm_calls,'tool_calls':result.tool_calls,'tokens':result.token_usage,
                            'elapsed_ms':int((time.monotonic()-request.state.started)*1000)}))
                except asyncio.CancelledError:
                    outcome='cancelled'
                    raise
                except Exception as exc:
                    logger.error(json.dumps({'event':'turn_failed','request_id':request.state.request_id,'error_type':type(exc).__name__}))
                    queue.put_nowait(('failure',{'status':'error','code':'turn_failed',
                        'content':'Lượt hỏi không hoàn tất. Server không lưu đáp án để khôi phục; chỉ gửi lại nếu bạn muốn tạo lượt mới.'}))
                finally:
                    if outcome!='completed':
                        try:
                            await asyncio.wait_for(asyncio.to_thread(state['store'].finish_turn,turn_id,outcome),timeout=2)
                        except Exception:
                            logger.error(json.dumps({'event':'turn_metadata_update_failed','request_id':request.state.request_id}))
                    queue.put_nowait(('done',{}))
            task=asyncio.create_task(work())
            try:
                yield ': connected\n\n'
                while True:
                    try:event,payload=await asyncio.wait_for(queue.get(),timeout=10)
                    except TimeoutError:
                        yield ': heartbeat\n\n'
                        continue
                    if event=='done':break
                    yield f'event: {event}\ndata: {json.dumps(payload,ensure_ascii=False)}\n\n'
            finally:
                task.cancel()
                try:await asyncio.wait_for(asyncio.gather(task,return_exceptions=True),timeout=3)
                except TimeoutError:pass
                semaphore.release()
        return StreamingResponse(stream(),media_type='text/event-stream',headers={'X-Accel-Buffering':'no'})

    return app


app = create_app()
