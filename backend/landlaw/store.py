"""Durable storage. SQLite is development-only; PostgreSQL is required in production."""
import json
import math
import sqlite3
import threading
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from .config import Settings
from .models import Chunk, Document, Evidence, Relation
from .security import digest, normalize, utcnow

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS releases(id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS app_state(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS documents(
 release_id TEXT NOT NULL REFERENCES releases(id), id TEXT NOT NULL, payload TEXT NOT NULL,
 title TEXT NOT NULL, document_number TEXT, project TEXT, source_kind TEXT NOT NULL,
 jurisdiction TEXT NOT NULL, PRIMARY KEY(release_id,id));
CREATE TABLE IF NOT EXISTS chunks(
 release_id TEXT NOT NULL, id TEXT NOT NULL, document_id TEXT NOT NULL, text TEXT NOT NULL,
 locator TEXT NOT NULL, parent_id TEXT, page INTEGER, checksum TEXT NOT NULL,
 embedding_model TEXT, embedding TEXT, PRIMARY KEY(release_id,id),
 FOREIGN KEY(release_id,document_id) REFERENCES documents(release_id,id));
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id)
 ON DELETE CASCADE, role TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS traces(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id)
 ON DELETE CASCADE, payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS counters(key TEXT PRIMARY KEY, value INTEGER NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS answer_cache(key TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES sessions(id)
 ON DELETE CASCADE,payload TEXT NOT NULL,expires_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS message_session_idx ON messages(session_id,created_at);
"""


class RateLimited(Exception):
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after


class Store:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.postgres = bool(settings.database_url.get_secret_value())
        self._lock = threading.RLock()
        self.pool = None
        self.conn = None
        if self.postgres:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            self.pool = ConnectionPool(
                settings.database_url.get_secret_value(), min_size=0, max_size=4,
                timeout=8, reconnect_timeout=15, kwargs={"row_factory": dict_row, "prepare_threshold": None, "connect_timeout": 8},
            )
        else:
            path = Path(settings.sqlite_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(path), check_same_thread=False, timeout=10)
            self.conn.row_factory = sqlite3.Row
            self.conn.executescript("PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;" + SQLITE_SCHEMA)
            self.conn.commit()

    def close(self):
        if self.pool:
            self.pool.close()
        if self.conn:
            self.conn.close()

    @contextmanager
    def transaction(self):
        if self.pool:
            with self.pool.connection() as conn:
                with conn.transaction():
                    yield conn
        else:
            with self._lock:
                try:
                    yield self.conn
                    self.conn.commit()
                except BaseException:
                    self.conn.rollback()
                    raise

    def execute(self, conn, sql, params=()):
        return conn.execute(sql.replace("?", "%s"), params or None) if self.postgres else conn.execute(sql, params)

    def rows(self, sql, params=()):
        with self.transaction() as conn:
            return [dict(r) for r in self.execute(conn, sql, params).fetchall()]

    def ready(self):
        self.rows("SELECT 1 AS ok FROM app_state LIMIT 1")
        return True

    def create_session(self, session_id, token):
        self.cleanup()
        with self.transaction() as conn:
            self.execute(conn, "INSERT INTO sessions VALUES(?,?,?)", (session_id, digest(token), utcnow().isoformat()))

    def authenticate(self, session_id, token):
        import hmac

        rows = self.rows("SELECT token_hash,created_at FROM sessions WHERE id=?", (session_id,))
        cutoff = (utcnow() - timedelta(days=self.settings.session_retention_days)).isoformat()
        return bool(rows and rows[0]["created_at"] >= cutoff and hmac.compare_digest(rows[0]["token_hash"], digest(token)))

    def cleanup(self):
        with self.transaction() as conn:
            self.execute(conn, "DELETE FROM sessions WHERE created_at<?", (
                (utcnow() - timedelta(days=self.settings.session_retention_days)).isoformat(),))
            self.execute(conn, "DELETE FROM counters WHERE expires_at<?", (utcnow().isoformat(),))
            self.execute(conn, "DELETE FROM answer_cache WHERE expires_at<?", (utcnow().isoformat(),))

    def cached_answer(self, key, session_id):
        rows = self.rows("SELECT payload FROM answer_cache WHERE key=? AND session_id=? AND expires_at>?",
                         (key, session_id, utcnow().isoformat()))
        return json.loads(rows[0]["payload"]) if rows else None

    def cache_answer(self, key, session_id, result):
        if result.status not in {"answered", "clarification_needed"}:
            return
        with self.transaction() as conn:
            self.execute(conn, "INSERT INTO answer_cache VALUES(?,?,?,?) ON CONFLICT(key) DO NOTHING",
                         (key, session_id, result.model_dump_json(), (utcnow()+timedelta(hours=24)).isoformat()))

    def prune_releases(self):
        """Retain active and previous corpus plus staged candidates from the last seven days."""
        keep = [value for value in (self.state("active_release"), self.state("previous_release")) if value]
        candidates = self.rows("SELECT id FROM releases WHERE created_at<?", ((utcnow()-timedelta(days=7)).isoformat(),))
        with self.transaction() as conn:
            for row in candidates:
                if row["id"] in keep:
                    continue
                for table in ("chunks", "documents", "releases"):
                    self.execute(conn, f"DELETE FROM {table} WHERE {'id' if table == 'releases' else 'release_id'}=?", (row["id"],))

    def messages(self, session_id, limit=20):
        rows = self.rows("SELECT role,payload,created_at FROM messages WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                         (session_id, limit))
        return [{"role": r["role"], "payload": json.loads(r["payload"]), "created_at": r["created_at"]} for r in reversed(rows)]

    def save_turn(self, session_id, message, result):
        import uuid

        now = utcnow().isoformat()
        with self.transaction() as conn:
            for role, payload in [("user", {"content": message}), ("assistant", result.model_dump(mode="json"))]:
                self.execute(conn, "INSERT INTO messages VALUES(?,?,?,?,?)",
                             (str(uuid.uuid4()), session_id, role, json.dumps(payload, ensure_ascii=False), now))
            self.execute(conn, "INSERT INTO traces VALUES(?,?,?,?)", (
                result.trace_id, session_id, json.dumps([e.model_dump() for e in result.trace], ensure_ascii=False), now))

    def trace(self, trace_id, session_id):
        rows = self.rows("SELECT payload FROM traces WHERE id=? AND session_id=?", (trace_id, session_id))
        return json.loads(rows[0]["payload"]) if rows else None

    def consume(self, limits: list[tuple[str, int, int]]):
        """Atomically reserve all counters or none, including across processes."""
        now = utcnow()
        with self.transaction() as conn:
            for key, limit, window in limits:
                expires = (now + timedelta(seconds=window)).isoformat()
                row = self.execute(conn, """INSERT INTO counters(key,value,expires_at) VALUES(?,1,?)
                    ON CONFLICT(key) DO UPDATE SET value=counters.value+1 RETURNING value""", (key, expires)).fetchone()
                if row["value"] > limit:
                    raise RateLimited(window)

    def state(self, key):
        rows = self.rows("SELECT value FROM app_state WHERE key=?", (key,))
        return rows[0]["value"] if rows else None

    def set_state(self, key, value):
        with self.transaction() as conn:
            self.execute(conn, "INSERT INTO app_state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def release(self, release_id=None):
        release_id = release_id or self.state("active_release")
        if not release_id:
            return None
        rows = self.rows("SELECT payload FROM releases WHERE id=?", (release_id,))
        return json.loads(rows[0]["payload"]) if rows else None

    def stage(self, payload):
        release_id = payload["id"]
        with self.transaction() as conn:
            if self.execute(conn, "SELECT id FROM releases WHERE id=?", (release_id,)).fetchone():
                raise ValueError("Release already exists: immutable content cannot be overwritten")
            self.execute(conn, "INSERT INTO releases VALUES(?,?,?)", (
                release_id, json.dumps(payload, ensure_ascii=False), utcnow().isoformat()))
            for item in payload["documents"]:
                doc = Document.model_validate(item)
                self.execute(conn, "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?)", (
                    release_id, doc.id, doc.model_dump_json(), doc.title, doc.document_number,
                    doc.project, doc.source_kind, doc.jurisdiction))
                for raw in item["chunks"]:
                    chunk = Chunk.model_validate(raw)
                    embedding = raw.get("embedding")
                    self.execute(conn, "INSERT INTO chunks(release_id,id,document_id,text,locator,parent_id,page,checksum,embedding_model,embedding) VALUES(?,?,?,?,?,?,?,?,?,?)", (
                        release_id, chunk.id, doc.id, chunk.text, chunk.locator, chunk.parent_id,
                        chunk.page, chunk.checksum, chunk.embedding_model,
                        json.dumps(embedding) if embedding else None))

    def publish(self, release_id):
        release = self.release(release_id)
        if not release:
            raise ValueError("Unknown release")
        old = self.state("active_release")
        with self.transaction() as conn:
            if old:
                self.execute(conn, "INSERT INTO app_state VALUES('previous_release',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (old,))
            self.execute(conn, "INSERT INTO app_state VALUES('active_release',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (release_id,))

    def documents(self, release_id=None):
        release_id = release_id or self.state("active_release")
        return [Document.model_validate_json(r["payload"]) for r in self.rows(
            "SELECT payload FROM documents WHERE release_id=? ORDER BY id", (release_id,))]

    def document(self, doc_id, release_id=None):
        release_id = release_id or self.state("active_release")
        rows = self.rows("SELECT payload FROM documents WHERE release_id=? AND id=?", (release_id, doc_id))
        return Document.model_validate_json(rows[0]["payload"]) if rows else None

    def chunk(self, chunk_id, release_id=None):
        release_id = release_id or self.state("active_release")
        rows = self.rows("SELECT * FROM chunks WHERE release_id=? AND id=?", (release_id, chunk_id))
        return self._chunk(rows[0]) if rows else None

    @staticmethod
    def _chunk(row):
        vector = row.get("embedding")
        if vector is not None:
            vector = json.loads(str(vector)) if isinstance(vector, str) else list(vector)
        return Chunk(**{k: row[k] for k in ["id", "document_id", "text", "locator", "parent_id", "page", "checksum", "embedding_model"]}, embedding=vector)

    def relations(self, doc_id, release_id=None):
        release = self.release(release_id)
        return [Relation.model_validate(r) for r in (release or {}).get("relations", [])
                if r["source_id"] == doc_id or r["target_id"] == doc_id]

    def search(self, query, vector=None, project=None, release_id=None, embedding_model=None):
        release_id = release_id or self.state("active_release")
        if not release_id:
            return []
        scope_sql = " AND (d.project IS NULL OR d.project=?)" if project else ""
        params = (release_id, project) if project else (release_id,)
        if self.postgres:
            lexical = self.rows("""SELECT c.*, ts_rank_cd(c.search_tsv, websearch_to_tsquery('simple',?)) AS rank
                FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id
                WHERE c.release_id=? AND c.search_tsv @@ websearch_to_tsquery('simple',?)""" + scope_sql +
                " ORDER BY rank DESC,c.id LIMIT 20", (normalize(query), release_id, normalize(query), *params[1:]))
            semantic = []
            if vector:
                semantic = self.rows("""SELECT c.* FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id
                    WHERE c.release_id=? AND c.embedding IS NOT NULL AND c.embedding_model=?""" + scope_sql +
                    " ORDER BY c.embedding <=> ?::vector LIMIT 20", (*params[:1], embedding_model, *params[1:], json.dumps(vector)))
        else:
            candidates = self.rows("""SELECT c.* FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id
                WHERE c.release_id=?""" + scope_sql, params)
            tokens = set(normalize(query).split())
            def lexical_score(r):
                text = normalize(r["text"])
                return sum(text.count(t) for t in tokens if len(t) > 1) / math.sqrt(max(1, len(text.split())))
            lexical = sorted((r for r in candidates if lexical_score(r) > 0), key=lexical_score, reverse=True)[:20]
            semantic = []
            if vector:
                def cosine(r):
                    v = json.loads(r["embedding"])
                    return sum(a*b for a, b in zip(v, vector, strict=True))
                semantic = sorted((r for r in candidates if r["embedding"] and r["embedding_model"] == embedding_model), key=cosine, reverse=True)[:20]
        scores, rows_by_id = {}, {}
        for branch in (lexical, semantic):
            for position, row in enumerate(branch, 1):
                scores[row["id"]] = scores.get(row["id"], 0) + 1 / (60 + position)
                rows_by_id[row["id"]] = row
        docs = {d.id: d for d in self.documents(release_id)}
        for chunk_id, row in rows_by_id.items():
            number = docs[row["document_id"]].document_number
            if number and normalize(number) in normalize(query):
                scores[chunk_id] += 0.1
        return [Evidence(chunk=self._chunk(rows_by_id[i]), document=docs[rows_by_id[i]["document_id"]], score=scores[i])
                for i in sorted(scores, key=lambda i: (-scores[i], i))[:8]]

    def backup(self, target: Path, include_sessions=False):
        # Only corpus/config; deliberately exclude session tokens and personal messages.
        payload = {"format": 1, "releases": self.rows("SELECT * FROM releases"),
                   "state": self.rows("SELECT * FROM app_state WHERE key IN ('active_release','previous_release')")}
        if include_sessions:
            from cryptography.fernet import Fernet
            key = self.settings.backup_encryption_key.get_secret_value()
            if not key:
                raise ValueError("Session backup requires BACKUP_ENCRYPTION_KEY; never archive plaintext sessions")
            self.cleanup()
            for table in ("sessions", "messages", "traces"):
                payload[table] = self.rows(f"SELECT * FROM {table}")
            content = Fernet(key.encode()).encrypt(json.dumps(payload, ensure_ascii=False).encode())
        else:
            content = json.dumps(payload, ensure_ascii=False).encode()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(0o600)

    def restore(self, source: Path):
        content = source.read_bytes()
        if not content.startswith(b"{"):
            from cryptography.fernet import Fernet
            key = self.settings.backup_encryption_key.get_secret_value()
            if not key:
                raise ValueError("Encrypted restore requires BACKUP_ENCRYPTION_KEY")
            content = Fernet(key.encode()).decrypt(content)
        payload = json.loads(content)
        if payload.get("format") != 1:
            raise ValueError("Unsupported backup format")
        for item in payload["releases"]:
            if not self.release(item["id"]):
                self.stage(json.loads(item["payload"]))
        for item in payload["state"]:
            self.set_state(item["key"], item["value"])
        if payload.get("sessions"):
            cutoff = (utcnow()-timedelta(days=self.settings.session_retention_days)).isoformat()
            session_ids = {row["id"] for row in payload["sessions"] if row["created_at"] >= cutoff}
            with self.transaction() as conn:
                for table, columns in [("sessions", ("id", "token_hash", "created_at")),
                                       ("messages", ("id", "session_id", "role", "payload", "created_at")),
                                       ("traces", ("id", "session_id", "payload", "created_at"))]:
                    for row in payload.get(table, []):
                        if (row["id"] if table == "sessions" else row["session_id"]) not in session_ids:
                            continue
                        self.execute(conn, f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)}) ON CONFLICT(id) DO NOTHING",
                                     tuple(row[c] for c in columns))
