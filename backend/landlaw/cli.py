import asyncio
import json
from pathlib import Path

import httpx
import typer
from pydantic import BaseModel, SecretStr

from .config import Settings
from .evaluation import evaluate, configuration_fingerprint
from .publication import validate_corpus
from .ingest import build_corpus, json_write
from .provider import Budget, GroqProvider
from .security import utcnow
from .store import Store

app = typer.Typer(no_args_is_help=True, pretty_exceptions_show_locals=False)


def reviewed_source_files(source):
    """Include original cached official responses as well as normalized parser input."""
    files = [(raw, source.get('raw_checksums', {}).get(raw)) for raw in source.get('raw_paths', [])]
    files.extend((item['path'], item['sha256']) for item in (source.get('source_snapshot') or {}).get('raw_snapshots', []))
    files.extend((item['ocr_path'], item['ocr_sha256']) for item in source.get('ocr_sidecars', [])
                 if item.get('review_status') == 'verified')
    files.extend((item['path'], item['sha256']) for item in source.get('source_artifacts', []))
    return files


@app.command()
def preflight(live: bool = False):
    """Inspect configuration; --live performs real generation and embedding probes."""
    settings = Settings()
    checks = {"groq_key": bool(settings.groq_api_key.get_secret_value()),
              "llm_provider": settings.llm_provider, "generation_model": settings.generation_model,
              "postgresql": bool(settings.database_url.get_secret_value()),
              "production_config": settings.app_env == "production"}
    async def probe():
        store = Store(settings)
        probe_store = Store(settings.model_copy(update={"database_url": SecretStr(""), "sqlite_path": str(settings.data_dir / "checkpoints/preflight.db")}))
        provider = GroqProvider(settings, probe_store)
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
                    checks["embedding_live"] = len(await provider.embed("Kiểm tra kết nối", query=True)) == settings.embedding_dimensions
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
def ingest(offline: bool = False, embed: bool = False, ocr: bool = False, cached_embeddings_only: bool = False, persist: bool = True):
    """Build a staging release. Never auto-publish changed legal content."""
    import logging
    logger = logging.getLogger('landlaw.ingest')
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    async def run():
        settings = Settings().for_operator()
        store, provider = Store(settings), None
        try:
            provider = GroqProvider(settings, store)
            payload, report = await build_corpus(settings, provider, offline, embed or cached_embeddings_only, ocr, cached_embeddings_only)
            if persist and not store.release(payload["id"],metadata_only=True):
                store.stage(payload)
            return report
        finally:
            if provider:
                await provider.close()
            store.close()
    typer.echo(json.dumps(asyncio.run(run()), ensure_ascii=False, indent=2))


@app.command()
def benchmark(split: str = "smoke", release_id: str | None = None, limit: int | None = None,
              concurrency: int = typer.Option(1,min=1,max=2), case_ids: str | None = None, mode: str = "agentic"):
    """Run/resume the academic twenty-case agentic suite."""
    if split != "smoke":
        raise typer.BadParameter("Only the academic smoke split is supported")
    if mode != 'agentic':
        raise typer.BadParameter('Only agentic evaluation is supported')
    modes = ('agentic',)
    async def run():
        settings = Settings().for_operator()
        store, provider = Store(settings), None
        try:
            provider = GroqProvider(settings, store)
            return await evaluate(settings, store, provider, split, release_id, limit,concurrency,
                set(case_ids.split(',')) if case_ids else None,
                modes)
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
def cleanup():
    store = Store(Settings().for_operator())
    try:
        store.cleanup()
        store.prune_releases()
        typer.echo("Expired sessions, messages, traces and counters removed.")
    finally:
        store.close()


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


@app.command()
def publish(release_id: str):
    """Publish a verified academic snapshot; no legal certification."""
    settings=Settings().for_operator()
    store=Store(settings)
    try:
        release=store.release(release_id)
        if not release:raise typer.BadParameter('Unknown release')
        validate_corpus(release)
        path=settings.data_dir/'backups'/f"prepublish-{utcnow().strftime('%Y%m%dT%H%M%S')}.json"
        store.backup(path)
        store.publish(release_id,{'profile':'academic','published_at':utcnow().isoformat(),
                                 'configuration_sha256':configuration_fingerprint(settings)})
        typer.echo(f'Published academic snapshot {release_id}; backup {path}')
    finally:store.close()


if __name__ == "__main__":
    app()
