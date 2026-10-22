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
from .retrieval import HeadingIndex, terms

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
CREATE TABLE IF NOT EXISTS counters(key TEXT PRIMARY KEY, value INTEGER NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS turns(id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
 fingerprint TEXT NOT NULL, status TEXT NOT NULL, lease_until TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS running_turn_session ON turns(session_id) WHERE status='running';
CREATE TABLE IF NOT EXISTS source_reviews(id TEXT PRIMARY KEY,release_id TEXT NOT NULL REFERENCES releases(id),
 document_id TEXT NOT NULL,checksum TEXT NOT NULL,checked_at TEXT NOT NULL,status TEXT NOT NULL,receipt text NOT NULL);
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
        self._heading_cache = OrderedDict()
        if self.postgres:
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            self.pool = ConnectionPool(
                settings.database_url.get_secret_value(), min_size=0, max_size=4,
                timeout=8, reconnect_timeout=15, kwargs={"row_factory": dict_row, "prepare_threshold": None,
                    "connect_timeout": 8, "options": f"-c statement_timeout={settings.db_statement_timeout_ms}", "autocommit": True, "keepalives": 1, "keepalives_idle": 30,
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
            self.execute(conn, "DELETE FROM turns WHERE created_at<?", ((utcnow()-timedelta(days=7)).isoformat(),))

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

    def start_turn(self, turn_id, session_id, fingerprint):
        now = utcnow()
        with self.transaction() as conn:
            # Lock session first: parallel requests serialize even with different IDs.
            suffix = ' FOR UPDATE' if self.postgres else ''
            self.execute(conn, 'SELECT id FROM sessions WHERE id=?'+suffix, (session_id,)).fetchone()
            self.execute(conn, "UPDATE turns SET status='expired' WHERE session_id=? AND status='running' AND lease_until<?", (session_id, now.isoformat()))
            existing = self.execute(conn, 'SELECT fingerprint,status FROM turns WHERE id=?', (turn_id,)).fetchone()
            if existing:
                return 'request_payload_conflict' if existing['fingerprint'] != fingerprint else 'request_'+existing['status']
            if self.execute(conn, "SELECT id FROM turns WHERE session_id=? AND status='running'", (session_id,)).fetchone():
                return 'session_busy'
            self.execute(conn, 'INSERT INTO turns VALUES(?,?,?,?,?,?)', (turn_id, session_id, fingerprint, 'running', (now+timedelta(seconds=120)).isoformat(), now.isoformat()))
        return None

    def finish_turn(self, turn_id, status):
        with self.transaction() as conn:
            self.execute(conn, 'UPDATE turns SET status=? WHERE id=?', (status, turn_id))

    def cooldown(self):
        value = self.state('provider_cooldown_until')
        if not value:
            return 0
        from datetime import datetime
        return max(0, math.ceil((datetime.fromisoformat(value)-utcnow()).total_seconds()))

    def set_cooldown(self, seconds):
        until = (utcnow()+timedelta(seconds=seconds)).isoformat()
        with self.transaction() as conn:
            self.execute(conn, "INSERT INTO app_state VALUES('provider_cooldown_until',?) ON CONFLICT(key) DO UPDATE SET value=CASE WHEN app_state.value<excluded.value THEN excluded.value ELSE app_state.value END", (until,))

    def reserve_public_llm(self):
        delay = self.cooldown()
        if delay:
            raise RateLimited(delay, source='provider')
        now=utcnow()
        key=f'usage:public:tokens:{now.date()}'
        rows=self.rows('SELECT value FROM counters WHERE key=?', (key,))
        if rows and rows[0]['value'] >= self.settings.public_daily_token_limit:
            raise RateLimited(86400, source='public_token_threshold')
        self.consume([(f'public:llm:{now.date()}', self.settings.public_daily_llm_limit, 86400)])

    def source_review_states(self, release, document_ids=None):
        """Review freshness is independent of legal effectivity at the question date.

        Only an otherwise reviewed snapshot can become stale. Changed receipts
        remain adverse until superseded for this checksum; unavailable, missing
        or invalid metadata is unknown, never a stale-snapshot permission.
        """
        from datetime import datetime
        now = utcnow()
        docs = {d['id']: d for d in release.get('documents', [])}
        selected = docs.keys() if document_ids is None else sorted(document_ids)
        states = {}
        def checked_time(value):
            try:
                stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return stamp if stamp.tzinfo is not None and stamp <= now else None
            except (ValueError, AttributeError, TypeError):
                return None
        # One release-level read preserves the latest-receipt rule without a
        # database round trip for every document on the public status path.
        latest = {}
        if release.get('id'):
            for row in self.rows("SELECT document_id,checksum,checked_at,status,receipt FROM source_reviews WHERE release_id=?",
                                 (release['id'],)):
                key = (row['document_id'], row['checksum'])
                if key not in latest or row['checked_at'] > latest[key]['checked_at']:
                    latest[key] = row
        for ident in selected:
            states[ident] = 'unknown'
            doc = docs.get(ident)
            if not doc or not doc.get('checksum') or not release.get('id'):
                continue
            reviews = [latest[(doc['id'], doc['checksum'])]] if (doc['id'], doc['checksum']) in latest else []
            if reviews:
                status = reviews[0]['status']
                if status == 'changed':
                    states[ident] = 'changed'
                    continue
                if status != 'unchanged':
                    continue
                try:
                    scoped = 'verified_scope' in json.loads(reviews[0]['receipt'])
                except (ValueError, TypeError):
                    continue
                if scoped:
                    # Reviewing selected passages never certifies the whole act.
                    states[ident] = 'stale'
                    continue
                stamp = checked_time(reviews[0]['checked_at'])
            else:
                times = [checked_time(doc.get('checked_at')), checked_time(release.get('checked_at'))]
                stamp = min(times) if all(times) else None
            if stamp is not None:
                states[ident] = 'fresh' if stamp >= now-timedelta(days=7) else 'stale'
        return states

    def source_fresh(self, release, document_ids=None):
        states = self.source_review_states(release, document_ids)
        return bool(states) and all(status == 'fresh' for status in states.values())

    def source_gate(self, release_id):
        value = self.state(f'source_gate:{release_id}')
        if value is None:
            return None
        try:
            policy = json.loads(value)
            receipts_valid = (isinstance(policy.get('receipts'), dict) and bool(policy['receipts'])
                              and all(isinstance(key, str) and isinstance(ident, str)
                                      and re.fullmatch(r'[0-9a-f]{64}', ident)
                                      for key, ident in policy['receipts'].items()))
            valid = (isinstance(policy, dict) and policy.get('release_id') == release_id
                     and receipts_valid and policy.get('version') == 1)
            if not valid and isinstance(policy, dict) and policy.get('version') == 2:
                valid = self._standing_policy_valid(policy, release_id)
            return policy if valid else {'invalid': True}
        except (ValueError, TypeError, AttributeError):
            return {'invalid': True}

    @staticmethod
    def _standing_policy_valid(policy, release_id):
        """A v2 gate is an explicit, reviewed migration to a standing snapshot.

        It must name the v1 policy it supersedes and pin the exact receipt and
        passage checksums that were reviewed under that older policy. A missing
        or malformed migration block fails closed instead of silently
        reinterpreting historical evidence.
        """
        if (policy.get('mode') != 'standing_verified_snapshot'
                or policy.get('release_id') != release_id
                or not isinstance(policy.get('receipts'), dict) or not policy['receipts']
                or not isinstance(policy.get('standing'), dict) or not policy['standing']
                or set(policy['standing']) != set(policy['receipts'])):
            return False
        supersedes = policy.get('supersedes')
        if (not isinstance(supersedes, dict) or supersedes.get('version') != 1
                or not isinstance(supersedes.get('policy_sha256'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', supersedes['policy_sha256'])):
            return False
        for doc_id, ident in policy['receipts'].items():
            entry = policy['standing'].get(doc_id)
            if (not isinstance(ident, str) or not re.fullmatch(r'[0-9a-f]{64}', ident)
                    or not isinstance(entry, dict)
                    or entry.get('receipt_sha256') != ident
                    or not isinstance(entry.get('reviewed_at'), str)
                    or not isinstance(entry.get('reviewed_as_of'), str)
                    or not isinstance(entry.get('chunks'), dict) or not entry['chunks']
                    or not isinstance(entry.get('standing_chunks'), dict)
                    or not (entry['standing_chunks'] or entry.get('legal_windows'))
                    or not all(isinstance(chunk_id, str) and isinstance(checksum, str)
                               and re.fullmatch(r'[0-9a-f]{64}', checksum)
                               for chunk_id, checksum in entry['chunks'].items())
                    or not all(chunk_id in entry['chunks']
                               and entry['chunks'][chunk_id] == checksum
                               for chunk_id, checksum in entry['standing_chunks'].items())):
                return False
            windows = entry.get('legal_windows', [])
            if not isinstance(windows, list):
                return False
            for scope in windows:
                if (not isinstance(scope, dict)
                        or not isinstance(scope.get('as_of_from'), str)
                        or not isinstance(scope.get('as_of_to'), str)
                        or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', scope['as_of_from'])
                        or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', scope['as_of_to'])
                        or scope['as_of_from'] >= scope['as_of_to']
                        or not isinstance(scope.get('chunk_checksums'), dict)
                        or not scope['chunk_checksums']
                        or any(chunk_id not in entry['chunks']
                               or entry['chunks'][chunk_id] != checksum
                               for chunk_id, checksum in scope['chunk_checksums'].items())):
                    return False
        return True

    def source_review_metadata(self, release):
        """Review identity for status and answer notices; never a legal-currency claim."""
        policy = self.source_gate((release or {}).get('id')) or {}
        if policy.get('version') == 2 and policy.get('standing'):
            reviewed = [entry.get('reviewed_at') for entry in policy['standing'].values()]
            reviewed_as_of = [entry.get('reviewed_as_of') for entry in policy['standing'].values()]
            return {'mode': 'standing_verified_snapshot',
                    'reviewed_at': max((value for value in reviewed if value), default=None),
                    'reviewed_as_of': max((value for value in reviewed_as_of if value), default=None),
                    'whole_corpus_verified': False,
                    'policy_sha256': digest(json.dumps(policy, ensure_ascii=False, sort_keys=True))}
        if policy.get('version') == 1:
            return {'mode': 'scoped_receipts', 'reviewed_at': None, 'reviewed_as_of': None,
                    'whole_corpus_verified': False,
                    'policy_sha256': digest(json.dumps(policy, ensure_ascii=False, sort_keys=True))}
        return {'mode': 'none', 'reviewed_at': None, 'reviewed_as_of': None,
                'whole_corpus_verified': False, 'policy_sha256': None}

    def scoped_source_reviews(self, release, passages, as_of, review_cache=None):
        """Pinned receipt gate for candidate passages.

        Version 1 keeps the original scoped date windows and receipt age limit.
        Version 2 is a standing verified snapshot: the exact pinned receipt and
        passage checksums are still required, the latest adverse receipt still
        wins, but operational age alone never invalidates reviewed evidence.
        Legal applicability is checked separately at the question date.
        """
        from datetime import date, datetime
        policy = self.source_gate((release or {}).get('id')) or {}
        docs = {d['id']: d for d in (release or {}).get('documents', [])}
        states = {}
        if review_cache is None:
            review_cache = {}
        for doc_id, chunk_id, checksum in passages:
            key = f'{doc_id}:{chunk_id}'
            states[key] = 'unknown'
            doc = docs.get(doc_id)
            if policy.get('version') not in {1, 2} or not doc:
                continue
            if doc_id not in review_cache:
                review_cache[doc_id] = self.rows('SELECT id,status,checked_at,receipt FROM source_reviews WHERE release_id=? '
                    'AND document_id=? AND checksum=? ORDER BY checked_at DESC LIMIT 1',
                    (release['id'], doc_id, doc['checksum']))
            rows = review_cache[doc_id]
            if not rows:
                continue
            row = rows[0]
            if row['status'] == 'changed':
                states[key] = 'changed'
                continue
            if row['status'] != 'unchanged' or row['id'] != policy.get('receipts', {}).get(doc_id):
                continue
            try:
                receipt = json.loads(row['receipt'])
                canonical = json.dumps(receipt, ensure_ascii=False, sort_keys=True)
                if digest(canonical) != row['id']:
                    continue
                stamp = datetime.fromisoformat(row['checked_at'].replace('Z', '+00:00'))
                if stamp.tzinfo is None or stamp > utcnow():
                    continue
                if policy.get('version') == 2:
                    entry = policy.get('standing', {}).get(doc_id) or {}
                    if (entry.get('receipt_sha256') != row['id']
                            or entry.get('chunks', {}).get(chunk_id) != checksum):
                        continue
                    # The passage checksum must also appear in the imported receipt's
                    # own reviewed scope; the migration cannot invent passage coverage.
                    if not any(scope.get('chunk_checksums', {}).get(chunk_id) == checksum
                               for scope in receipt.get('verified_scope', [])
                               if isinstance(scope, dict)):
                        continue
                    if entry.get('standing_chunks', {}).get(chunk_id) == checksum:
                        states[key] = 'standing'
                        continue
                    for scope in entry.get('legal_windows', []):
                        if (scope.get('chunk_checksums', {}).get(chunk_id) == checksum
                                and date.fromisoformat(scope['as_of_from']) <= as_of
                                and as_of < date.fromisoformat(scope['as_of_to'])):
                            states[key] = 'reviewed_window'
                            break
                    continue
                if stamp < utcnow()-timedelta(days=7):
                    states[key] = 'stale'
                    continue
                for scope in receipt.get('verified_scope', []):
                    if (scope['chunk_checksums'].get(chunk_id) == checksum
                            and date.fromisoformat(scope['as_of_from']) <= as_of
                            and as_of < date.fromisoformat(scope['as_of_to'])):
                        states[key] = 'fresh'
                        break
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
        return states

    def admissible_chunk_scope(self, release, as_of):
        """Reviewed passages that the active policy admits on ``as_of``.

        Retrieval uses this only to keep reviewed evidence from being crowded
        out by unreviewed candidates. Every returned passage is still re-checked
        with ``scoped_source_reviews`` and legal applicability before generation.
        """
        release = release or {}
        policy = self.source_gate(release.get('id'))
        if not isinstance(policy, dict) or policy.get('version') not in {1, 2}:
            return {}
        from datetime import date
        docs = {d['id']: d for d in release.get('documents', [])}
        latest = {}
        for row in self.rows('SELECT id,document_id,checksum,checked_at,status,receipt '
                             'FROM source_reviews WHERE release_id=?', (release.get('id'),)):
            key = (row['document_id'], row['checksum'])
            if key not in latest or row['checked_at'] > latest[key]['checked_at']:
                latest[key] = row
        scope = {}
        if policy.get('version') == 2:
            entries = policy.get('standing', {})
        else:
            entries = {doc_id: {'receipt_sha256': ident} for doc_id, ident in policy.get('receipts', {}).items()}
        for doc_id, entry in entries.items():
            doc = docs.get(doc_id)
            row = latest.get((doc_id, doc.get('checksum'))) if doc else None
            if (not doc or not row or row['status'] != 'unchanged'
                    or row['id'] != policy.get('receipts', {}).get(doc_id)):
                continue
            try:
                from datetime import datetime
                from .security import digest, utcnow
                receipt = json.loads(row['receipt'])
                if digest(json.dumps(receipt, ensure_ascii=False, sort_keys=True)) != row['id']:
                    continue
                stamp = datetime.fromisoformat(row['checked_at'].replace('Z', '+00:00'))
                if stamp.tzinfo is None or stamp > utcnow():
                    continue
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
            if policy.get('version') == 2:
                if entry.get('receipt_sha256') != row['id']:
                    continue
                eligible = dict(entry.get('standing_chunks') or {})
                for window in entry.get('legal_windows') or []:
                    try:
                        if date.fromisoformat(window['as_of_from']) <= as_of < date.fromisoformat(window['as_of_to']):
                            eligible.update(window.get('chunk_checksums') or {})
                    except (ValueError, KeyError, TypeError):
                        continue
            else:
                if stamp < utcnow() - timedelta(days=7):
                    continue
                eligible = {}
                for window in receipt.get('verified_scope') or []:
                    try:
                        if date.fromisoformat(window['as_of_from']) <= as_of < date.fromisoformat(window['as_of_to']):
                            eligible.update(window.get('chunk_checksums') or {})
                    except (ValueError, KeyError, TypeError):
                        continue
            reviewed_scopes = receipt.get('verified_scope') or []
            for chunk_id, checksum in eligible.items():
                if policy.get('version') == 2 and entry.get('chunks', {}).get(chunk_id) != checksum:
                    continue
                if not any(window.get('chunk_checksums', {}).get(chunk_id) == checksum
                           for window in reviewed_scopes if isinstance(window, dict)):
                    continue
                scope[chunk_id] = checksum
        return scope

    def source_gate_status(self, release, as_of=None):
        from datetime import date
        from .security import local_date
        from .source_policy import applicability
        target = as_of or local_date()
        policy = self.source_gate((release or {}).get('id'))
        if policy is None:
            return None
        if policy.get('version') == 2:
            return self._standing_gate_status(policy, release, target, applicability)
        latest = {}
        for row in self.rows('SELECT id,document_id,checksum,checked_at,status,receipt FROM source_reviews WHERE release_id=?',
                             ((release or {}).get('id'),)):
            key = (row['document_id'], row['checksum'])
            if key not in latest or row['checked_at'] > latest[key]['checked_at']:
                latest[key] = row
        docs = {d['id']: d for d in (release or {}).get('documents', [])}
        review_cache = {}
        for doc_id in (policy.get('receipts') or {}):
            doc = docs.get(doc_id)
            row = latest.get((doc_id, doc.get('checksum'))) if doc else None
            review_cache[doc_id] = [row] if row else []
        approved = set()
        for doc_id, ident in (policy.get('receipts') or {}).items():
            rows = review_cache.get(doc_id) or []
            if not rows or rows[0]['id'] != ident:
                continue
            try:
                scopes = json.loads(rows[0]['receipt']).get('verified_scope', [])
                # Evaluate every reviewed window for this document from the
                # receipt fetched once above.
                passages = [(doc_id, cid, checksum) for scope in scopes
                            for cid, checksum in scope['chunk_checksums'].items()]
                states = self.scoped_source_reviews(release, passages, target, review_cache)
                approved.update(key for key, status in states.items() if status == 'fresh')
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
        return {'mode': 'scoped_receipts',
                'policy_sha256': digest(json.dumps(policy, ensure_ascii=False, sort_keys=True)),
                'eligible_passages': len(approved), 'usable': bool(approved),
                'review_mode': 'scoped_receipts', 'operational_expiry': None,
                'whole_corpus_verified': False}

    def _standing_gate_status(self, policy, release, target, applicability):
        """Count exact reviewed passages that are legally applicable at target.

        The receipt age is intentionally not part of this calculation. A latest
        adverse receipt still removes its document, and a passage is counted only
        when its checksum matches both the standing policy and the imported
        receipt's reviewed scope. The returned mode names the snapshot rather
        than asserting that the whole corpus or current law is verified.
        """
        from datetime import date
        latest = {}
        for row in self.rows('SELECT id,document_id,checksum,checked_at,status,receipt FROM source_reviews WHERE release_id=?',
                             ((release or {}).get('id'),)):
            key = (row['document_id'], row['checksum'])
            if key not in latest or row['checked_at'] > latest[key]['checked_at']:
                latest[key] = row
        docs = {d['id']: d for d in (release or {}).get('documents', [])}
        chunk_ids = [chunk_id for entry in policy.get('standing', {}).values()
                     for chunk_id in entry.get('chunks', {})]
        chunks = {}
        if chunk_ids:
            placeholders = ','.join('?' * len(chunk_ids))
            for row in self.rows(f'SELECT * FROM chunks WHERE release_id=? AND id IN ({placeholders})',
                                 ((release or {}).get('id'), *chunk_ids)):
                chunks[row['id']] = row
        approved = []
        reviewed = []
        reviewed_as_of = []
        for doc_id, entry in (policy.get('standing') or {}).items():
            doc = docs.get(doc_id)
            ident = entry.get('receipt_sha256')
            row = latest.get((doc_id, doc.get('checksum'))) if doc else None
            if not doc or not row or row['id'] != ident or row['status'] != 'unchanged':
                continue
            try:
                receipt = json.loads(row['receipt'])
                if digest(json.dumps(receipt, ensure_ascii=False, sort_keys=True)) != row['id']:
                    continue
            except (ValueError, TypeError):
                continue
            eligible = {}
            for chunk_id, checksum in (entry.get('standing_chunks') or {}).items():
                eligible[chunk_id] = checksum
            for scope in entry.get('legal_windows', []):
                try:
                    if date.fromisoformat(scope['as_of_from']) <= target < date.fromisoformat(scope['as_of_to']):
                        eligible.update(scope.get('chunk_checksums') or {})
                except (ValueError, KeyError, TypeError):
                    continue
            doc_model = None
            for chunk_id, checksum in eligible.items():
                if entry.get('chunks', {}).get(chunk_id) != checksum:
                    continue
                chunk = chunks.get(chunk_id)
                if (not chunk or chunk['document_id'] != doc_id or chunk['checksum'] != checksum
                        or digest(chunk['text']) != checksum):
                    continue
                if not any(scope.get('chunk_checksums', {}).get(chunk_id) == checksum
                           for scope in receipt.get('verified_scope', []) if isinstance(scope, dict)):
                    continue
                try:
                    doc_model = doc_model or Document.model_validate(doc)
                    chunk_model = self._chunk(chunk)
                    if applicability(doc_model, target, chunk_model) not in {'current', 'provision_specific', 'context'}:
                        continue
                except (ValueError, TypeError):
                    continue
                approved.append(f'{doc_id}:{chunk_id}')
            reviewed.append(entry.get('reviewed_at'))
            reviewed_as_of.append(entry.get('reviewed_as_of'))
        return {'mode': 'standing_verified_snapshot',
                'policy_sha256': digest(json.dumps(policy, ensure_ascii=False, sort_keys=True)),
                'eligible_passages': len(approved), 'usable': bool(approved),
                'review_mode': 'standing_verified_snapshot',
                'reviewed_at': max((value for value in reviewed if value), default=None),
                'reviewed_as_of': max((value for value in reviewed_as_of if value), default=None),
                'operational_expiry': None,
                'whole_corpus_verified': False,
                'legal_applicability_checked_at': str(target)}

    def consume(self, limits: list[tuple[str, int, int]]):
        return self.consume_weighted([(key,limit,window,1) for key,limit,window in limits])

    def operational_review(self, doc, release_id):
        """Latest receipt controls operational claims, including changes and unavailable sources."""
        from datetime import datetime
        rows=self.rows('SELECT receipt FROM source_reviews WHERE release_id=? AND document_id=? AND checksum=? '
                       'ORDER BY checked_at DESC LIMIT 1',(release_id,doc.id,doc.checksum))
        if not rows:
            return doc
        receipt=json.loads(rows[0]['receipt'])
        reviewed=receipt.get('operational_review') or {}
        explicit=all(reviewed.get(key) is True for key in
                     ('source_role_checked','jurisdiction_checked','procedure_and_dependencies_checked'))
        return doc.model_copy(update={'operational_review_status':receipt['status'] if explicit else 'pending',
            'operational_reviewed_at':datetime.fromisoformat(receipt['checked_at'].replace('Z','+00:00')) if explicit else None})

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
        for profile in ('academic', 'accepted', 'demo', 'technical_demo'):
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
        self.backup(backup_path)
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
        if any(d.get('project') not in (None,'ring4') for d in release['documents']):
            raise ValueError('Only Ring4 and shared legal sources may be published')
        old = self.state("active_release")
        with self.transaction() as conn:
            if publication:
                if publication.get('profile') not in {'academic'}:
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
                ranked = sorted(candidates, key=relevance, reverse=True)
                if not clause:
                    # Opening an article must retain its opening scope/actors.
                    # Ranking only by query overlap can select continuation
                    # lists and lose the clause to which they belong.
                    opening = next((row for row in candidates if re.search(
                        rf'\bĐiều\s+{number}\s*[.:]', row['text'], re.I)), None)
                    if opening:
                        ranked = [opening] + [row for row in ranked if row['id'] != opening['id']]
                groups.append(ranked)
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

    def heading_index(self, release_id):
        with self._lock:
            headings=self._heading_cache.get(release_id)
            if headings is None:
                rows=self.rows("SELECT id,document_id,locator,substr(text,1,700) AS prefix FROM chunks WHERE release_id=? AND substr(id,length(id)-6)<>'-parent'",(release_id,))
                headings=HeadingIndex(rows)
                self._heading_cache[release_id]=headings
                while len(self._heading_cache)>1:self._heading_cache.popitem(last=False)
            return headings

    def article_candidates(self, query, release_id, as_of, project=None):
        docs=self.documents(release_id)
        eligible={d.id for d in docs if (not project or d.project in {None,project})
                  and (not d.effective_from or d.effective_from<=as_of)
                  and (not d.effective_to or as_of<d.effective_to)}
        # Historical documents remain in the catalogue and searchable tools;
        # this suggestion list prioritizes headings at the requested time.
        return self.heading_index(release_id).articles(query,eligible)

    def search(self, query, vector=None, project=None, release_id=None, embedding_model=None, as_of=None):
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
        # Effectivity questions need the operative replacement, not only hits
        # mentioning the old act. These are source relations, not inferred law.
        replacement_rows = []
        if any(term in normalized_query for term in ('hieu luc', 'thay the', 'bai bo')):
            metadata = self.release(release_id, metadata_only=True) or {}
            years = set(re.findall(r'\b(?:19|20)\d{2}\b', normalized_query))
            topics = [term for term in ('boi thuong', 'tai dinh cu', 'gia dat', 'quy hoach') if term in normalized_query]
            targets = set(exact_docs)
            if not targets and years and topics and 'ha noi' in normalized_query:
                targets = {d.id for d in docs.values() if d.jurisdiction.lower() == 'hanoi'
                    and any('/'+year+'/' in (d.document_number or '') for year in years)
                    and any(term in normalize(d.title) for term in topics)}
            for relation in metadata.get('relations', []):
                if len(replacement_rows) >= 6:
                    break
                source = docs.get(relation['source_id'])
                if (relation['type'] != 'replaces' or relation['target_id'] not in targets or not source
                        or source.source_kind != 'legal' or not source.applicability_verified
                        or (project and source.project not in {None, project})
                        or (as_of and (not source.effective_from or source.effective_from > as_of
                            or (source.effective_to and as_of >= source.effective_to)))):
                    continue
                locator = relation.get('source_locator') or relation.get('locator')
                if not locator:
                    continue
                opened = self.open_document(source.id, release_id, locator, query)
                if opened:
                    replacement_rows.extend(c.model_dump() for c in opened.chunks)
        headings = self.heading_index(release_id)
        eligible={d.id for d in docs.values() if not project or d.project in {None,project}}
        release_meta = self.release(release_id, True) or {}
        admitted_scope = self.admissible_chunk_scope(release_meta, as_of) if as_of else {}
        heading_scores=headings.rank(query,eligible,exact_docs)
        heading_ids=[item[1] for item in heading_scores]
        heading_rows=self.rows(f"SELECT {projection} FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id WHERE c.release_id=? AND c.id IN ({','.join('?' for _ in heading_ids)})", (release_id,*heading_ids)) if heading_ids else []
        heading_lookup={r['id']:r for r in heading_rows}
        heading_rows=[heading_lookup[i] for i in heading_ids]
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
        admitted_lexical, admitted_semantic = [], []
        if self.postgres:
            lexical = self.rows(f"""SELECT {projection}, ts_rank_cd(c.search_tsv, websearch_to_tsquery('simple',?)) AS rank
                FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id
                WHERE c.release_id=? AND c.search_tsv @@ websearch_to_tsquery('simple',?)""" + scope_sql +
                " ORDER BY rank DESC,c.id LIMIT 20", (normalize(query), release_id, normalize(query), *params[1:]))
            if len(lexical) < 8:
                keywords = list(dict.fromkeys(terms(query)))[:40]
                if keywords:
                    disjunction = " OR ".join(keywords)
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
            if admitted_scope:
                admitted_ids = list(admitted_scope)
                admitted_sql = " AND c.id IN (" + ",".join("?" for _ in admitted_ids) + ")"
                scope_params = (project,) if project else ()
                admitted_lexical = self.rows(f"""SELECT {projection}, ts_rank_cd(c.search_tsv, websearch_to_tsquery('simple',?)) AS rank
                    FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id
                    WHERE c.release_id=? AND c.search_tsv @@ websearch_to_tsquery('simple',?)""" + scope_sql + admitted_sql +
                    " ORDER BY rank DESC,c.id LIMIT 12", (normalize(query), release_id, *scope_params, *admitted_ids))
                if vector:
                    dimensions = len(vector)
                    admitted_semantic = self.rows(f"""SELECT {projection} FROM chunks c JOIN documents d ON d.id=c.document_id AND d.release_id=c.release_id
                        WHERE c.release_id=? AND c.embedding IS NOT NULL AND c.embedding_model=? AND vector_dims(c.embedding)={dimensions}""" + scope_sql + admitted_sql +
                        f" ORDER BY c.embedding::vector({dimensions}) <=> ?::vector({dimensions}) LIMIT 12",
                        (release_id, embedding_model, *scope_params, *admitted_ids, json.dumps(vector)))
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
            if admitted_scope:
                admitted_candidates = [r for r in candidates if r['id'] in admitted_scope]
                admitted_lexical = sorted((r for r in admitted_candidates if lexical_score(r) > 0),
                                          key=lexical_score, reverse=True)[:12]
                if vector:
                    admitted_semantic = sorted((r for r in admitted_candidates if r['embedding']
                        and r['embedding_model'] == embedding_model and len(json.loads(r['embedding'])) == len(vector)),
                        key=cosine, reverse=True)[:12]
        scores, rows_by_id = {}, {}
        for branch in (lexical, semantic, heading_rows, exact, replacement_rows):
            for position, row in enumerate(branch, 1):
                scores[row["id"]] = scores.get(row["id"], 0) + 1 / (60 + position)
                rows_by_id[row["id"]] = row
        for chunk_id, row in rows_by_id.items():
            if row['document_id'] in exact_docs:
                scores[chunk_id] += 0.1
            if article and row['id'] in {r['id'] for r in exact}:
                scores[chunk_id] += 0.2
            if row['id'] in {r['id'] for r in replacement_rows}:
                scores[chunk_id] += 0.15
            doc=docs[row['document_id']]
            temporal=any(t in normalized_query for t in ('lich su','chuyen tiep','hieu luc','thay the','bai bo','nam 2023','nam 2013'))
            if as_of and doc.id not in exact_docs and not temporal:
                if (doc.effective_to and as_of>=doc.effective_to) or (doc.effective_from and as_of<doc.effective_from):
                    scores[chunk_id] *= .35
        # Keep the ordinary ranking first. Reviewed passages that the ordinary
        # branches already found retain their exact position; the reviewed-only
        # branch appends rescued passages instead of reshuffling stronger hits.
        admitted_scores, admitted_rows = {}, {}
        for branch in (admitted_lexical, admitted_semantic):
            for position, row in enumerate(branch, 1):
                admitted_scores[row["id"]] = admitted_scores.get(row["id"], 0) + 1 / (60 + position)
                admitted_rows[row["id"]] = row
        main_order = sorted(scores, key=lambda i: (-scores[i], i))
        admitted_main = [i for i in main_order if i in admitted_scope]
        admitted_extra = [i for i in sorted(admitted_scores, key=lambda i: (-admitted_scores[i], i))
                          if i not in rows_by_id]
        for chunk_id in admitted_extra:
            rows_by_id[chunk_id] = admitted_rows[chunk_id]
            scores[chunk_id] = admitted_scores[chunk_id]
        order = admitted_main + admitted_extra + [i for i in main_order if i not in admitted_scope]
        reviewed = {}
        if as_of and self.source_gate(release_id) is not None:
            # Reuse the active legal review, without changing admission rules.
            # Stale hits must not crowd out reviewed evidence.
            reviewed = self.scoped_source_reviews(release_meta,
                [(r['document_id'], r['id'], r['checksum']) for r in rows_by_id.values()], as_of)
            admitted_order = [i for i in order
                              if reviewed.get(rows_by_id[i]['document_id']+':'+i) in
                              {'fresh', 'standing', 'reviewed_window'}]
            order = admitted_order + [i for i in order if i not in admitted_order]
        return [Evidence(chunk=self._chunk(rows_by_id[i]), document=docs[rows_by_id[i]["document_id"]], score=scores[i])
                for i in order[:8]]

    def backup(self, target: Path, include_sessions=False):
        # Only corpus/config; deliberately exclude session tokens and personal messages.
        payload = {"format": 1, "releases": self.rows("SELECT * FROM releases"),
                   "state": self.rows("SELECT * FROM app_state WHERE key IN ('active_release','previous_release') OR key LIKE 'publication:%' OR key LIKE 'source_gate:%'")}
        if include_sessions:
            raise ValueError('Conversation backups are disabled; browser-owned history only')
        content = json.dumps(payload, ensure_ascii=False).encode()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.chmod(0o600)

    def restore(self, source: Path):
        with self._lock:
            self._metadata_cache.clear()
        content = source.read_bytes()
        if not content.startswith(b"{"):
            raise ValueError('Only corpus-only JSON backups are accepted')
        payload = json.loads(content)
        if payload.get("format") != 1 or set(payload) != {'format','releases','state'}:
            raise ValueError('Only corpus/config backups without conversation data are accepted')
        for item in payload["releases"]:
            if not self.release(item["id"]):
                self.stage(self.decode_release(item["payload"]))
        for item in payload["state"]:
            self.set_state(item["key"], item["value"])
