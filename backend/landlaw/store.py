"""Durable storage. SQLite is development-only; PostgreSQL is required in production."""
import json
import base64
import gzip
import math
import re
import sqlite3
import threading
from collections import OrderedDict
from copy import deepcopy
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from .config import Settings
from .models import Chunk, Document, Evidence, Relation
from .security import digest, normalize, utcnow

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS releases(id TEXT PRIMARY KEY, payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS release_metadata(id TEXT PRIMARY KEY REFERENCES releases(id) ON DELETE CASCADE, payload TEXT NOT NULL);
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
    def __init__(self, retry_after: int = 60, source: str = 'application'):
        self.retry_after = retry_after
        self.source = source
        super().__init__(f"{source} quota exceeded; retry_after={retry_after}s")


class Store:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.postgres = bool(settings.database_url.get_secret_value())
        self._lock = threading.RLock()
        self.pool = None
        self.conn = None
        self._metadata_cache = OrderedDict()
        if self.postgres:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            self.pool = ConnectionPool(
                settings.database_url.get_secret_value(), min_size=0, max_size=4,
                timeout=8, reconnect_timeout=15, kwargs={"row_factory": dict_row, "prepare_threshold": None,
                    "connect_timeout": 8, "autocommit": True, "keepalives": 1, "keepalives_idle": 30,
                    "keepalives_interval": 10, "keepalives_count": 3, "tcp_user_timeout": 60000},
            )
        else:
            path = Path(settings.sqlite_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(path), check_same_thread=False, timeout=10)
            self.conn.row_factory = sqlite3.Row
            self.conn.executescript("PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;" + SQLITE_SCHEMA)
            for row in self.conn.execute('SELECT id,payload FROM releases WHERE id NOT IN (SELECT id FROM release_metadata)').fetchall():
                metadata = self.decode_release(row['payload'])
                metadata['documents'] = [{k:v for k,v in d.items() if k!='chunks'} for d in metadata['documents']]
                self.conn.execute('INSERT INTO release_metadata VALUES(?,?)',(row['id'],json.dumps(metadata,ensure_ascii=False)))
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
        if self.pool:
            # Read-only queries need one round trip; writes still use explicit transactions.
            with self.pool.connection() as conn:
                return [dict(r) for r in self.execute(conn, sql, params).fetchall()]
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

        now = utcnow()
        with self.transaction() as conn:
            for index, (role, payload) in enumerate([("user", {"content": message}), ("assistant", result.model_dump(mode="json"))]):
                self.execute(conn, "INSERT INTO messages VALUES(?,?,?,?,?)",
                             (str(uuid.uuid4()), session_id, role, json.dumps(payload, ensure_ascii=False),
                              (now + timedelta(microseconds=index)).isoformat()))
            self.execute(conn, "INSERT INTO traces VALUES(?,?,?,?)", (
                result.trace_id, session_id, json.dumps([e.model_dump() for e in result.trace], ensure_ascii=False), now.isoformat()))

    def trace(self, trace_id, session_id):
        rows = self.rows("SELECT payload FROM traces WHERE id=? AND session_id=?", (trace_id, session_id))
        return json.loads(rows[0]["payload"]) if rows else None

    def consume(self, limits: list[tuple[str, int, int]]):
        return self.consume_weighted([(key,limit,window,1) for key,limit,window in limits])

    def record_usage(self, kind, units=1):
        """Count provider usage without imposing an application quota."""
        if units < 1:
            return
        now = utcnow()
        with self.transaction() as conn:
            self.execute(conn, """INSERT INTO counters(key,value,expires_at) VALUES(?,?,?)
                ON CONFLICT(key) DO UPDATE SET value=counters.value+excluded.value""",
                (f"usage:{kind}:{now.date()}", units, (now+timedelta(days=8)).isoformat()))

    def consume_weighted(self, limits: list[tuple[str,int,int,int]]):
        """Atomically reserve all counters or none, including across processes."""
        now = utcnow()
        with self.transaction() as conn:
            for key, limit, window, units in limits:
                if units < 1 or units > limit:
                    raise RateLimited(window)
                expires = (now + timedelta(seconds=window)).isoformat()
                row = self.execute(conn, """INSERT INTO counters(key,value,expires_at) VALUES(?,?,?)
                    ON CONFLICT(key) DO UPDATE SET value=counters.value+excluded.value RETURNING value""", (key, units, expires)).fetchone()
                if row["value"] > limit:
                    raise RateLimited(window)

    def state(self, key):
        rows = self.rows("SELECT value FROM app_state WHERE key=?", (key,))
        return rows[0]["value"] if rows else None

    def set_state(self, key, value):
        with self.transaction() as conn:
            self.execute(conn, "INSERT INTO app_state VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def release(self, release_id=None, metadata_only=False):
        release_id = release_id or self.state("active_release")
        if not release_id:
            return None
        if metadata_only:
            with self._lock:
                cached = self._metadata_cache.get(release_id)
                if cached is not None:
                    self._metadata_cache.move_to_end(release_id)
                    return deepcopy(cached)
        if metadata_only:
            rows = self.rows("SELECT payload FROM release_metadata WHERE id=?", (release_id,))
        else:
            rows = self.rows("SELECT payload FROM releases WHERE id=?", (release_id,))
        if not rows:
            return None
        result = json.loads(rows[0]['payload']) if metadata_only else self.decode_release(rows[0]['payload'])
        if metadata_only:
            with self._lock:
                self._metadata_cache[release_id] = deepcopy(result)
                while len(self._metadata_cache) > 2:
                    self._metadata_cache.popitem(last=False)
        return result

    @staticmethod
    def decode_release(payload):
        if payload.startswith('gzip:'):
            payload = gzip.decompress(base64.b64decode(payload[5:])).decode()
        return json.loads(payload)

    def stage(self, payload):
        release_id = payload["id"]
        serialized = json.dumps(payload, ensure_ascii=False)
        # Vector archives compress well; metadata and searchable chunks remain separate.
        archived = 'gzip:'+base64.b64encode(gzip.compress(serialized.encode(),mtime=0)).decode()
        if self.postgres:
            used = self.rows("SELECT pg_database_size(current_database()) AS size")[0]['size']
            if used + len(archived.encode()) * 2 > 350 * 1024 * 1024:
                raise ValueError("Staging would exceed the 350 MB database reserve; prune reviewed releases first")
        with self.transaction() as conn:
            if self.execute(conn, "SELECT id FROM releases WHERE id=?", (release_id,)).fetchone():
                raise ValueError("Release already exists: immutable content cannot be overwritten")
            self.execute(conn, "INSERT INTO releases VALUES(?,?,?)", (
                release_id, archived, utcnow().isoformat()))
            metadata = {**payload, "documents": [{k: v for k, v in d.items() if k != "chunks"} for d in payload["documents"]]}
            self.execute(conn, "INSERT INTO release_metadata VALUES(?,?)", (release_id, json.dumps(metadata, ensure_ascii=False)))
            document_rows, chunk_rows = [], []
            for item in payload["documents"]:
                doc = Document.model_validate(item)
                document_rows.append((
                    release_id, doc.id, doc.model_copy(update={'chunks':[]}).model_dump_json(), doc.title, doc.document_number,
                    doc.project, doc.source_kind, doc.jurisdiction))
                for raw in item["chunks"]:
                    chunk = Chunk.model_validate(raw)
                    embedding = raw.get("embedding")
                    chunk_rows.append((
                        release_id, chunk.id, doc.id, chunk.text, chunk.locator, chunk.parent_id,
                        chunk.page, chunk.checksum, chunk.embedding_model,
                        json.dumps(embedding) if embedding else None))
            batches = [("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?)", document_rows),
                       ("INSERT INTO chunks(release_id,id,document_id,text,locator,parent_id,page,checksum,embedding_model,embedding) VALUES(?,?,?,?,?,?,?,?,?,?)", chunk_rows)]
            for statement, records in batches:
                if self.postgres:
                    with conn.cursor() as cursor:
                        cursor.executemany(statement.replace("?", "%s"), records)
                else:
                    conn.executemany(statement, records)

    def publication(self, release_id=None):
        release_id = release_id or self.state('active_release')
        for profile in ('accepted', 'demo', 'technical_demo'):
            value = self.state(f'publication:{release_id}:{profile}') if release_id else None
            if value:
                return json.loads(value)
        return None

    def retire_staging(self, release_ids, backup_path):
        """Retire unpublished staging only after a recoverable full backup."""
        if not release_ids or len(set(release_ids)) != len(release_ids):
            raise ValueError('Choose distinct staging releases')
        protected = {self.state('active_release'), self.state('previous_release')}
        for release_id in release_ids:
            if release_id in protected or self.publication(release_id) or not self.release(release_id, metadata_only=True):
                raise ValueError('Only existing unpublished staging releases can be retired')
        self.backup(backup_path, include_sessions=True)
        with self.transaction() as conn:
            for release_id in release_ids:
                # Recheck pointers inside the deletion transaction.
                for key in ('active_release', 'previous_release'):
                    row = self.execute(conn, 'SELECT value FROM app_state WHERE key=?', (key,)).fetchone()
                    if row and row['value'] == release_id:
                        raise ValueError('Release became protected; retirement canceled')
                self.execute(conn, 'DELETE FROM chunks WHERE release_id=?', (release_id,))
                self.execute(conn, 'DELETE FROM documents WHERE release_id=?', (release_id,))
                self.execute(conn, 'DELETE FROM releases WHERE id=?', (release_id,))

    def unpublish(self):
        """Withdraw the first release without deleting sessions or corpus."""
        with self.transaction() as conn:
            self.execute(conn,"DELETE FROM app_state WHERE key='active_release'")

    def publish(self, release_id, publication=None):
        release = self.release(release_id)
        if not release:
            raise ValueError("Unknown release")
        old = self.state("active_release")
        with self.transaction() as conn:
            if publication:
                if publication.get('profile') not in {'technical_demo','demo','accepted'}:
                    raise ValueError('Invalid publication profile')
                key = f"publication:{release_id}:{publication['profile']}"
                value = json.dumps(publication,sort_keys=True,ensure_ascii=False)
                existing = self.execute(conn,'SELECT value FROM app_state WHERE key=?',(key,)).fetchone()
                if existing and existing['value'] != value:
                    raise ValueError('Publication evidence is immutable')
                self.execute(conn,'INSERT INTO app_state VALUES(?,?) ON CONFLICT(key) DO NOTHING',(key,value))
            if old:
                self.execute(conn, "INSERT INTO app_state VALUES('previous_release',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (old,))
            self.execute(conn, "INSERT INTO app_state VALUES('active_release',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (release_id,))

    def documents(self, release_id=None):
        release_id = release_id or self.state("active_release")
        release = self.release(release_id, metadata_only=True)
        return [Document.model_validate(d) for d in (release or {}).get("documents", [])]

    def document(self, doc_id, release_id=None):
        release_id = release_id or self.state("active_release")
        return next((d for d in self.documents(release_id) if d.id == doc_id),None)

    def open_document(self, doc_id, release_id=None, locator=None, query=None):
        """Bounded read tool: fetch relevant passages without the entire price-table archive."""
        release_id = release_id or self.state('active_release')
        doc = next((d for d in self.documents(release_id) if d.id == doc_id), None)
        if not doc:
            return None
        articles = list(dict.fromkeys(re.findall(r'\bdieu\s+(\d+[a-z]?)\b', normalize(locator or ''))))[:3]
        projection = 'id,document_id,text,locator,parent_id,page,checksum,embedding_model'
        base = f"SELECT {projection} FROM chunks WHERE release_id=? AND document_id=? AND substr(id,length(id)-6) <> '-parent'"
        if not articles:
            rows = self.rows(base + ' ORDER BY id LIMIT 3', (release_id, doc_id))
        else:
            # A long article can span many chunks. Opening its first three loses
            # late clauses (notably transitional rules). Rank bounded candidates
            # using the requested clause and question, and retain each article.
            clause = re.search(r'\bkhoan\s+(\d+)\b', normalize(locator or ''))
            terms = set(re.findall(r'[a-z0-9]{3,}', normalize(query or locator or '')))
            def relevance(row):
                body = normalize(row['text'])
                exact_clause = bool(clause and re.search(rf'(?<!\d){clause[1]}\.\s', body))
                return (exact_clause, sum(body.count(term) for term in terms) / math.sqrt(max(1, len(body.split()))))
            groups = []
            for number in articles:
                candidates = self.rows(base + ' AND (locator=? OR locator=?) ORDER BY page,id LIMIT 20',
                                       (release_id, doc_id, f'Điều {number}', f'Điều {number} · ngữ cảnh'))
                groups.append(sorted(candidates, key=relevance, reverse=True))
            rows = [group[0] for group in groups if group]
            extras = sorted([row for group in groups for row in group[1:]], key=relevance, reverse=True)
            rows += extras[:3-len(rows)]
        doc.chunks = [self._chunk(r) for r in rows[:3]]
        return doc

    def chunk(self, chunk_id, release_id=None):
        release_id = release_id or self.state("active_release")
        rows = self.rows("SELECT * FROM chunks WHERE release_id=? AND id=?", (release_id, chunk_id))
        return self._chunk(rows[0]) if rows else None

    def open_effectivity(self, doc_id, release_id=None):
        """Read operative effectivity text instead of a preamble or arbitrary first article."""
        release_id=release_id or self.state('active_release')
        doc=self.document(doc_id,release_id)
        if not doc:return None
        rows=self.rows('SELECT id,document_id,text,locator,parent_id,page,checksum,embedding_model FROM chunks '
            'WHERE release_id=? AND document_id=? AND text LIKE ? ORDER BY length(text),id LIMIT 20',
            (release_id,doc_id,'%hiệu lực%'))
        selected=[row for row in rows if any(phrase in normalize(row['text']) for phrase in
            ('quyet dinh nay co hieu luc','nghi dinh nay co hieu luc','luat nay co hieu luc','nghi quyet nay co hieu luc'))]
        doc.chunks=[self._chunk(row) for row in selected[:3]]
        return doc

    @staticmethod
    def _chunk(row):
        vector = row.get("embedding")
        if vector is not None:
            vector = json.loads(str(vector)) if isinstance(vector, str) else list(vector)
        return Chunk(**{k: row[k] for k in ["id", "document_id", "text", "locator", "parent_id", "page", "checksum", "embedding_model"]}, embedding=vector)

    def relations(self, doc_id, release_id=None):
        release = self.release(release_id, metadata_only=True)
        return [Relation.model_validate(r) for r in (release or {}).get("relations", [])
                if r["source_id"] == doc_id or r["target_id"] == doc_id]

    def search(self, query, vector=None, project=None, release_id=None, embedding_model=None):
        release_id = release_id or self.state("active_release")
        if not release_id:
            return []
        # Parent rows are expanded after retrieval; letting them compete with
        # their own children crowds out precise article/paragraph citations.
        scope_sql = " AND substr(c.id,length(c.id)-6) <> '-parent'" + (" AND (d.project IS NULL OR d.project=?)" if project else "")
        params = (release_id, project) if project else (release_id,)
        projection = 'c.id,c.document_id,c.text,c.locator,c.parent_id,c.page,c.checksum,c.embedding_model' if self.postgres else 'c.*'
        docs = {d.id: d for d in self.documents(release_id)}
        normalized_query=normalize(query)
        def exact_document(document):
            number=normalize(document.document_number or '')
            if number and number in normalized_query:return True
            # Citizens commonly name a law and its year instead of its number.
            # Preserve the year so similarly named historical laws cannot match.
            title=re.sub(r'^luat so \S+\s+luat\s+', 'luat ', normalize(document.title)).rstrip('.')
            year=re.search(r'/(\d{4})/',number)
            if not year or not title.startswith('luat ') or 'sua doi' in title:return False
            title=re.sub(r'\s+\d{4}$','',title)
            return bool(re.search(r'\b'+re.escape(title)+r'(?:\s+nam)?\s+'+year[1]+r'\b',normalized_query))
        exact_docs = [d.id for d in docs.values() if exact_document(d)]
        article = re.search(r"\bdieu\s+(\d+[a-z]?)\b", normalize(query))
        exact = []
        if exact_docs:
            exact_sql = " AND d.id IN (" + ",".join("?" for _ in exact_docs) + ")"
            exact_params = [*params, *exact_docs]
            if article:
                exact_sql += " AND (c.locator=? OR c.locator=?)"
                exact_params.extend([f"Điều {article[1]}", f"Điều {article[1]} · ngữ cảnh"])
            exact = self.rows(f"""SELECT {projection} FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id
                WHERE c.release_id=?""" + scope_sql + exact_sql + " ORDER BY c.id LIMIT 20", tuple(exact_params))
        if self.postgres:
            lexical = self.rows(f"""SELECT {projection}, ts_rank_cd(c.search_tsv, websearch_to_tsquery('simple',?)) AS rank
                FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id
                WHERE c.release_id=? AND c.search_tsv @@ websearch_to_tsquery('simple',?)""" + scope_sql +
                " ORDER BY rank DESC,c.id LIMIT 20", (normalize(query), release_id, normalize(query), *params[1:]))
            if len(lexical) < 8:
                terms = list(dict.fromkeys(re.findall(r"[a-z0-9]{2,}", normalize(query))))[:40]
                if terms:
                    disjunction = " OR ".join(terms)
                    fallback = self.rows(f"""SELECT {projection}, ts_rank_cd(c.search_tsv, websearch_to_tsquery('simple',?)) AS rank
                        FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id
                        WHERE c.release_id=? AND c.search_tsv @@ websearch_to_tsquery('simple',?)""" + scope_sql +
                        " ORDER BY rank DESC,c.id LIMIT 20", (disjunction, release_id, disjunction, *params[1:]))
                    used = {r['id'] for r in lexical}
                    lexical += [r for r in fallback if r['id'] not in used][:20-len(lexical)]
            semantic = []
            if vector:
                dimensions = len(vector)
                if dimensions not in {384,768,1024}:
                    raise ValueError('Unsupported query vector dimension')
                semantic = self.rows(f"""SELECT {projection} FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id
                    WHERE c.release_id=? AND c.embedding IS NOT NULL AND c.embedding_model=? AND vector_dims(c.embedding)={dimensions}""" + scope_sql +
                    f" ORDER BY c.embedding::vector({dimensions}) <=> ?::vector({dimensions}) LIMIT 20", (*params[:1], embedding_model, *params[1:], json.dumps(vector)))
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
                semantic = sorted((r for r in candidates if r["embedding"] and r["embedding_model"] == embedding_model
                    and len(json.loads(r['embedding']))==len(vector)), key=cosine, reverse=True)[:20]
        scores, rows_by_id = {}, {}
        for branch in (lexical, semantic, exact):
            for position, row in enumerate(branch, 1):
                scores[row["id"]] = scores.get(row["id"], 0) + 1 / (60 + position)
                rows_by_id[row["id"]] = row
        for chunk_id, row in rows_by_id.items():
            number = docs[row["document_id"]].document_number
            if row['document_id'] in exact_docs:
                scores[chunk_id] += 0.1
            if article and row['id'] in {r['id'] for r in exact}:
                scores[chunk_id] += 0.2
        return [Evidence(chunk=self._chunk(rows_by_id[i]), document=docs[rows_by_id[i]["document_id"]], score=scores[i])
                for i in sorted(scores, key=lambda i: (-scores[i], i))[:8]]

    def backup(self, target: Path, include_sessions=False):
        # Only corpus/config; deliberately exclude session tokens and personal messages.
        payload = {"format": 1, "releases": self.rows("SELECT * FROM releases"),
                   "state": self.rows("SELECT * FROM app_state WHERE key IN ('active_release','previous_release') OR key LIKE 'publication:%'")}
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
        with self._lock:
            self._metadata_cache.clear()
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
                self.stage(self.decode_release(item["payload"]))
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
