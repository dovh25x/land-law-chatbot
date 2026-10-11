import asyncio
import json
from pathlib import Path

import httpx
import typer
from pydantic import BaseModel, SecretStr

from .config import Settings
from .evaluation import evaluate
from .ingest import build_corpus, coverage, json_write
from .provider import Budget, Gemini
from .security import utcnow
from .store import Store

app = typer.Typer(no_args_is_help=True)


@app.command()
def provision_runtime(rotate_existing: bool = False):
    """Create a restricted backend login; keep owner credentials offline in .env."""
    import secrets
    from urllib.parse import quote, urlencode
    from dotenv import set_key
    import psycopg
    from psycopg import sql

    settings = Settings().for_operator()
    owner = settings.database_url.get_secret_value()
    if not owner:
        raise typer.BadParameter("Owner database connection missing")
    from psycopg.conninfo import conninfo_to_dict
    info = conninfo_to_dict(owner)
    username = info.get("user", "")
    password = secrets.token_urlsafe(40)
    login = "landlaw_api" + ("." + username.split(".", 1)[1] if "." in username else "")
    host = info.get("host", "")
    if ":" in host:
        host = f"[{host}]"
    host += f":{int(info['port'])}" if info.get("port") else ""
    runtime = f"postgresql://{quote(login, safe='')}:{quote(password, safe='')}@{host}/{quote(info.get('dbname', 'postgres'), safe='')}?{urlencode({'sslmode': 'require'})}"
    with psycopg.connect(owner, prepare_threshold=None) as conn:
        if not conn.execute("SELECT rolcreaterole OR rolsuper FROM pg_roles WHERE rolname=current_user").fetchone()[0]:
            raise typer.BadParameter("Connection does not have permission to provision roles")
        exists = bool(conn.execute("SELECT 1 FROM pg_roles WHERE rolname='landlaw_api'").fetchone())
        if exists and not rotate_existing:
            raise typer.BadParameter("landlaw_api already exists; keep its existing credentials")
        conn.execute(sql.SQL("ALTER ROLE landlaw_api PASSWORD {}" if exists else "CREATE ROLE landlaw_api LOGIN PASSWORD {}").format(sql.Literal(password)))
        conn.execute("GRANT landlaw_runtime TO landlaw_api")
    # Keep local operator ability without deploying owner credentials to Render.
    set_key(".env", "ADMIN_DATABASE_URL", owner)
    set_key(".env", "DATABASE_URL", runtime)
    if not settings.ip_hash_secret.get_secret_value():
        set_key(".env", "IP_HASH_SECRET", secrets.token_hex(32))
    typer.echo("Restricted runtime login provisioned. Owner connection retained offline; no secrets printed.")


@app.command()
def preflight(live: bool = False):
    """Inspect configuration; --live performs real generation and embedding probes."""
    settings = Settings()
    checks = {"gemini_key": bool(settings.gemini_api_key.get_secret_value()),
              "postgresql": bool(settings.database_url.get_secret_value()),
              "supabase_storage": bool(settings.supabase_url and settings.supabase_service_role_key.get_secret_value()),
              "production_config": settings.app_env == "production"}
    async def probe():
        store = Store(settings)
        probe_store = Store(settings.model_copy(update={"database_url": SecretStr(""), "sqlite_path": str(settings.data_dir / "checkpoints/preflight.db")}))
        provider = Gemini(settings, probe_store)
        try:
            try:
                checks["database_ready"] = await asyncio.to_thread(store.ready)
            except Exception:
                checks["database_ready"] = False
            if live and provider.configured:
                class Probe(BaseModel):
                    ok: bool
                try:
                    await provider.generate(Probe, "Trả về ok=true. Kiểm tra kết nối kỹ thuật.", {}, Budget())
                    checks["generation_live"] = True
                    checks["embedding_live"] = len(await provider.embed("Kiểm tra kết nối", query=True)) == 768
                except Exception as exc:
                    checks["generation_or_embedding_error"] = type(exc).__name__
                    if type(exc).__name__ in {"ProviderUnavailable", "RateLimited"}:
                        checks["provider_error"] = str(exc)
        finally:
            await provider.close()
            probe_store.close()
            store.close()
    asyncio.run(probe())
    json_write(settings.reports_dir / "preflight.json", {"checked_at": utcnow().isoformat(), "checks": checks})
    typer.echo(json.dumps(checks, ensure_ascii=False, indent=2))


@app.command()
def migrate():
    """Apply PostgreSQL migration once with an owner/admin DATABASE_URL."""
    settings = Settings().for_operator()
    if not settings.database_url.get_secret_value():
        typer.echo("PostgreSQL DATABASE_URL not configured. SQLite schema is created automatically.")
        raise typer.Exit(1)
    import psycopg
    with psycopg.connect(settings.database_url.get_secret_value(), prepare_threshold=None) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS public.landlaw_migrations(version text PRIMARY KEY)")
        for path in sorted(Path("migrations").glob("[0-9][0-9][0-9]_*.sql")):
            version = path.name[:3]
            if not conn.execute("SELECT version FROM public.landlaw_migrations WHERE version=%s", (version,)).fetchone():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO public.landlaw_migrations VALUES(%s)", (version,))
                typer.echo(f"Migration {version} applied.")


@app.command()
def ingest(offline: bool = False, embed: bool = False, ocr: bool = False):
    """Build a staging release. Never auto-publish changed legal content."""
    async def run():
        settings = Settings().for_operator()
        store, provider = Store(settings), None
        try:
            provider = Gemini(settings, store)
            payload, report = await build_corpus(settings, provider, offline, embed, ocr)
            if not store.release(payload["id"]):
                store.stage(payload)
            return report
        finally:
            if provider:
                await provider.close()
            store.close()
    typer.echo(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))


@app.command()
def publish(release_id: str):
    """Require reviewed complete corpus and acceptance evidence for this exact release."""
    settings = Settings().for_operator()
    store = Store(settings)
    try:
        release = store.release(release_id)
        if not release:
            raise typer.BadParameter("Unknown release")
        corpus = coverage(release)
        path = settings.reports_dir / "latest.json"
        evaluation = json.loads(path.read_text()) if path.exists() else {}
        if not corpus["publication_ready"]:
            raise typer.BadParameter("Corpus missing verified metadata, embeddings or required coverage")
        if not (evaluation.get("acceptance_passed") and evaluation.get("split") == "acceptance" and evaluation.get("release") == release_id):
            raise typer.BadParameter("Reviewed acceptance benchmark for this exact release is required")
        backup_path = settings.data_dir / "backups" / f"prepublish-{utcnow().strftime('%Y%m%dT%H%M%S')}.json"
        store.backup(backup_path)
        store.publish(release_id)
        json_write(settings.data_dir / "releases" / f"{release_id}.json", release)
        typer.echo(f"Published {release_id}; backup {backup_path}")
    finally:
        store.close()


@app.command()
def benchmark(split: str = "dev", release_id: str | None = None, limit: int | None = None):
    """Run/resume real paired benchmark. Evaluate staging before publishing."""
    if split not in {"dev", "acceptance"}:
        raise typer.BadParameter("split must be dev or acceptance")
    async def run():
        settings = Settings().for_operator()
        store, provider = Store(settings), None
        try:
            provider = Gemini(settings, store)
            return await evaluate(settings, store, provider, split, release_id, limit)
        finally:
            if provider:
                await provider.close()
            store.close()
    typer.echo(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))


@app.command()
def backup(output: Path = Path("data/backups/latest.json"), include_sessions: bool = False):
    store = Store(Settings().for_operator())
    try:
        store.backup(output, include_sessions=include_sessions)
        typer.echo(f"Backup: {output}. Sessions {'encrypted' if include_sessions else 'excluded'}.")
    finally:
        store.close()


@app.command()
def restore(source: Path):
    store = Store(Settings().for_operator())
    try:
        store.restore(source)
        typer.echo("Corpus/config restored.")
    finally:
        store.close()


@app.command()
def rollback():
    store = Store(Settings().for_operator())
    try:
        previous = store.state("previous_release")
        if not previous:
            raise typer.BadParameter("No previous release")
        store.publish(previous)
        typer.echo(f"Active release: {previous}")
    finally:
        store.close()


@app.command()
def cleanup():
    store = Store(Settings().for_operator())
    try:
        store.cleanup()
        store.prune_releases()
        typer.echo("Expired sessions, messages, traces and counters removed.")
    finally:
        store.close()


@app.command()
def upload(release_file: Path):
    """Upload complete reviewed corpus into a private immutable Supabase bucket."""
    settings = Settings()
    payload = json.loads(release_file.read_text())
    if not coverage(payload)["publication_ready"]:
        raise typer.BadParameter("Only reviewed embedded complete releases may be uploaded")
    if not settings.supabase_url or not settings.supabase_service_role_key.get_secret_value():
        raise typer.BadParameter("Supabase Storage credentials missing")
    async def run():
        headers = {"Authorization": f"Bearer {settings.supabase_service_role_key.get_secret_value()}",
                   "apikey": settings.supabase_service_role_key.get_secret_value()}
        async with httpx.AsyncClient(timeout=60) as client:
            bucket = await client.get(f"{settings.supabase_url}/storage/v1/bucket/{settings.supabase_bucket}", headers=headers)
            if bucket.status_code == 404:
                bucket = await client.post(f"{settings.supabase_url}/storage/v1/bucket", headers=headers,
                    json={"id": settings.supabase_bucket, "name": settings.supabase_bucket, "public": False})
            if bucket.status_code >= 400:
                raise ValueError("Cannot create/read private bucket")
            if bucket.json().get("public"):
                raise ValueError("Corpus bucket must be private")
            response = await client.post(f"{settings.supabase_url}/storage/v1/object/{settings.supabase_bucket}/{payload['id']}/corpus.json",
                headers={**headers, "Content-Type": "application/json", "x-upsert": "false"}, content=release_file.read_bytes())
            if response.status_code not in {200, 201, 409}:
                raise ValueError("Storage upload failed")
    asyncio.run(run())
    typer.echo("Private corpus archive uploaded.")


@app.command()
def smoke(base_url: str):
    """Verify deployed readiness and a real authenticated answer, never print session tokens."""
    async def run():
        async with httpx.AsyncClient(timeout=180) as client:
            ready = await client.get(base_url.rstrip("/") + "/readyz")
            if ready.status_code != 200:
                raise ValueError("Deployed backend not ready")
            session = await client.post(base_url.rstrip("/") + "/api/v1/sessions")
            session.raise_for_status()
            data = session.json()
            response = await client.post(base_url.rstrip("/") + "/api/v1/chat", headers={"Authorization": f"Bearer {data['token']}"},
                json={"session_id": data["session_id"], "message": "Cần kiểm tra căn cứ nào để xác định điều kiện bồi thường khi thu hồi đất ở Hà Nội?"})
            response.raise_for_status()
            events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
            answer = next((e for e in events if "trace_id" in e), None)
            passed = bool(answer and answer["status"] in {"answered", "clarification_needed"} and answer["citations"] and answer["llm_calls"])
            report = {"checked_at": utcnow().isoformat(), "base_url": base_url, "passed": passed,
                      "status": (answer or {}).get("status"), "trace_id": (answer or {}).get("trace_id")}
            json_write(Path("reports/deployment-smoke.json"), report)
            if not passed:
                raise ValueError("No successful live answer with citations")
            return report
    typer.echo(json.dumps(asyncio.run(run()), indent=2))


if __name__ == "__main__":
    app()
