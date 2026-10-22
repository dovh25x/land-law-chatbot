"""Operator-only metadata commands. Never archive or expose conversation bodies."""
import hashlib
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from .security import utcnow, official_url


def record_source_review(store, receipt_path: Path):
    receipt=json.loads(receipt_path.read_text())
    release=store.release(None,True)
    doc=next((d for d in (release or {}).get('documents',[]) if d['id']==receipt['document_id']),None)
    if not doc or doc['checksum']!=receipt.get('checksum'):
        raise ValueError('Receipt must match an active source checksum')
    checked=datetime.fromisoformat(receipt['checked_at'].replace('Z','+00:00'))
    if checked.tzinfo is None or checked>utcnow() or checked<utcnow()-timedelta(days=7):
        raise ValueError('Receipt requires a recent, non-future timezone-aware check')
    if receipt.get('status') not in {'unchanged','changed','unavailable'}:
        raise ValueError('Unknown source check status')
    attachments = {item['url'] for item in doc.get('source_files', [])}
    def reviewed_url(url):
        return official_url(url) or (url in attachments and
            official_url(url, doc.get('publication_url') or doc['url']))
    if not receipt.get('relation_review') or not receipt.get('evidence_urls') or not all(reviewed_url(url) for url in receipt['evidence_urls']):
        raise ValueError('Require source evidence URLs and explicit amendment/transition review')
    if 'verified_scope' in receipt:
        from datetime import date
        scopes = receipt['verified_scope']
        if not isinstance(scopes, list) or not scopes:
            raise ValueError('Verified scope must contain explicit passages and date bounds')
        for scope in scopes:
            if (not isinstance(scope, dict) or not scope.get('chunk_checksums')
                    or date.fromisoformat(scope['as_of_from']) >= date.fromisoformat(scope['as_of_to'])):
                raise ValueError('Invalid verified scope')
            for ident, checksum in scope['chunk_checksums'].items():
                chunk = store.chunk(ident, release['id'])
                if not chunk or chunk.document_id != doc['id'] or chunk.checksum != checksum:
                    raise ValueError('Verified scope must match immutable source passages')
    if receipt.get('operational_review') is not None:
        operational=receipt['operational_review']
        if (not isinstance(operational,dict) or operational.get('source_role_checked') is not True
                or operational.get('jurisdiction_checked') is not True
                or operational.get('procedure_and_dependencies_checked') is not True):
            raise ValueError('Operational review must explicitly cover source role, jurisdiction and dependencies')
    encoded=json.dumps(receipt,ensure_ascii=False,sort_keys=True)
    ident=hashlib.sha256(encoded.encode()).hexdigest()
    with store.transaction() as conn:
        store.execute(conn,'INSERT INTO source_reviews VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
            (ident,release['id'],doc['id'],doc['checksum'],checked.isoformat(),receipt['status'],encoded))
    return {'receipt_sha256':ident,'document_id':doc['id'],'status':receipt['status']}


def _policy_sha256(policy):
    return hashlib.sha256(json.dumps(policy, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def build_standing_policy(store, base_policy=None):
    """Derive a v2 standing snapshot from the active v1 scoped policy.

    This is deliberately not a new source review. It preserves every original
    receipt hash and reviewed passage checksum, records the v1 policy it
    supersedes, and only removes the operational receipt-age/review-window
    condition. Legal applicability still comes from each document's own
    effective dates and provision validity at question time.
    """
    release = store.release(None, True)
    if not release:
        raise ValueError('Standing policy requires an active release')
    base = base_policy or store.source_gate(release['id'])
    if (not isinstance(base, dict) or base.get('version') != 1
            or base.get('release_id') != release['id']
            or not isinstance(base.get('receipts'), dict) or not base['receipts']):
        raise ValueError('Standing policy requires the current v1 scoped source gate')
    standing = {}
    for doc_id, ident in base['receipts'].items():
        rows = store.rows('SELECT id,status,checked_at,receipt FROM source_reviews WHERE id=? AND release_id=?',
                          (ident, release['id']))
        if not rows or rows[0]['status'] != 'unchanged':
            raise ValueError(f'Standing policy refuses a missing or adverse receipt: {doc_id}')
        receipt = json.loads(rows[0]['receipt'])
        scopes = receipt.get('verified_scope')
        if not isinstance(scopes, list) or not scopes:
            raise ValueError(f'Standing policy requires scoped passages: {doc_id}')
        chunks, standing_chunks, legal_windows = {}, {}, []
        for scope in scopes:
            try:
                start = date.fromisoformat(scope['as_of_from'])
                end = date.fromisoformat(scope['as_of_to'])
                scope_chunks = dict(scope['chunk_checksums'])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f'Invalid verified scope in {doc_id}') from None
            for chunk_id, checksum in scope_chunks.items():
                if chunks.get(chunk_id, checksum) != checksum:
                    raise ValueError(f'Conflicting passage checksum in {doc_id}')
                chunks[chunk_id] = checksum
            if (end - start).days <= 2:
                # Daily rotation windows are operational. Their content becomes
                # the standing snapshot; legal applicability is checked at the
                # question date against the document itself.
                standing_chunks.update(scope_chunks)
            else:
                # Longer intervals are the reviewer's explicit substantive date
                # scope and are preserved exactly, not extended.
                legal_windows.append({'as_of_from': scope['as_of_from'],
                                      'as_of_to': scope['as_of_to'],
                                      'chunk_checksums': scope_chunks})
        if not chunks or not (standing_chunks or legal_windows):
            raise ValueError(f'Standing policy requires at least one reviewed passage: {doc_id}')
        checked = str(receipt.get('checked_at') or rows[0]['checked_at'])[:10]
        standing[doc_id] = {
            'receipt_sha256': ident,
            'reviewed_at': receipt.get('checked_at') or rows[0]['checked_at'],
            'reviewed_as_of': checked,
            'chunks': chunks,
            'standing_chunks': standing_chunks,
            'legal_windows': legal_windows,
        }
    return {
        'version': 2,
        'mode': 'standing_verified_snapshot',
        'release_id': release['id'],
        'supersedes': {'version': 1, 'policy_sha256': _policy_sha256(base)},
        'receipts': dict(base['receipts']),
        'standing': standing,
    }


def activate_source_gate(store, policy_path: Path):
    """Pin an operator-reviewed receipt set without changing source content."""
    policy = json.loads(policy_path.read_text())
    release = store.release(None, True)
    if not release or policy.get('release_id') != release['id']:
        raise ValueError('Source gate requires an active release')
    if policy.get('version') == 1:
        if not isinstance(policy.get('receipts'), dict) or not policy['receipts']:
            raise ValueError('Source gate requires pinned receipts')
        for doc_id, ident in policy['receipts'].items():
            rows = store.rows('SELECT document_id,checksum,receipt FROM source_reviews WHERE id=? AND release_id=?',
                              (ident, release['id']))
            doc = next((d for d in release['documents'] if d['id'] == doc_id), None)
            if (not rows or rows[0]['document_id'] != doc_id or not doc
                    or rows[0]['checksum'] != doc['checksum']
                    or not json.loads(rows[0]['receipt']).get('verified_scope')):
                raise ValueError('Source gate requires imported checksum-bound scoped receipts')
    elif policy.get('version') == 2:
        if not store._standing_policy_valid(policy, release['id']):
            raise ValueError('Standing snapshot policy is malformed or incomplete')
        current = store.source_gate(release['id'])
        if current and current.get('version') == 1:
            if _policy_sha256(current) != policy['supersedes']['policy_sha256']:
                raise ValueError('Standing policy does not supersede the currently active v1 policy')
            if current.get('receipts') != policy.get('receipts'):
                raise ValueError('Standing policy must preserve the exact v1 receipt cohort')
        elif current and current.get('version') == 2:
            if _policy_sha256(current) != _policy_sha256(policy):
                raise ValueError('A different standing policy is already active; roll back explicitly first')
        elif current:
            raise ValueError('Standing policy requires an active valid source gate')
        for doc_id, ident in policy['receipts'].items():
            entry = policy['standing'][doc_id]
            rows = store.rows('SELECT document_id,checksum,status,receipt FROM source_reviews WHERE id=? AND release_id=?',
                              (ident, release['id']))
            doc = next((d for d in release['documents'] if d['id'] == doc_id), None)
            if (not rows or rows[0]['document_id'] != doc_id or not doc
                    or rows[0]['status'] != 'unchanged' or rows[0]['checksum'] != doc['checksum']):
                raise ValueError('Standing policy requires a matching unchanged receipt')
            receipt = json.loads(rows[0]['receipt'])
            reviewed = {chunk_id: checksum for scope in receipt.get('verified_scope', []) if isinstance(scope, dict)
                        for chunk_id, checksum in (scope.get('chunk_checksums') or {}).items()}
            if reviewed != entry['chunks']:
                raise ValueError('Standing policy must preserve every reviewed passage checksum')
            covered = set(entry['standing_chunks'])
            for scope in entry['legal_windows']:
                covered |= set(scope['chunk_checksums'])
            if covered != set(entry['chunks']):
                raise ValueError('Standing policy must keep every reviewed passage reachable')
            for chunk_id, checksum in entry['chunks'].items():
                chunk = store.chunk(chunk_id, release['id'])
                if not chunk or chunk.document_id != doc_id or chunk.checksum != checksum:
                    raise ValueError('Standing policy passage does not match a reviewed checksum')
    else:
        raise ValueError('Unknown source gate policy version')
    encoded = json.dumps(policy, ensure_ascii=False, sort_keys=True)
    store.set_state(f"source_gate:{release['id']}", encoded)
    return {'release_id': release['id'], 'policy_sha256': hashlib.sha256(encoded.encode()).hexdigest()}


def status(store):
    release=store.release(None,True)
    fresh=bool(release) and store.source_fresh(release)
    gate=store.source_gate_status(release)
    sources_available=gate['usable'] if gate is not None else (fresh or store.settings.allow_stale_generation)
    cutoff=(utcnow()-timedelta(hours=1)).isoformat()
    turns=store.rows('SELECT status,COUNT(*) AS count FROM turns WHERE created_at>? GROUP BY status',(cutoff,))
    failed=sum(r['count'] for r in turns if r['status'] in {'error','expired'})
    partial = bool(gate and gate.get('usable') and gate.get('review_mode') == 'standing_verified_snapshot')
    return {'checked_at':utcnow().isoformat(),'database':store.ready(),'corpus':(release or {}).get('id'),
        'sources_fresh':fresh,'generation_enabled':store.settings.generation_enabled,
        'source_gate':gate,
        'allow_stale_generation':store.settings.allow_stale_generation,
        'warnings':[] if fresh else (['source_partial_review'] if partial else ['source_stale']),
        'provider_cooldown_seconds':store.cooldown(),'last_hour_turns':{r['status']:r['count'] for r in turns},
        'needs_attention':failed>=5 or not release or not sources_available,
        'usage':[{'kind':r['key'],'units':r['value']} for r in store.rows("SELECT key,value FROM counters WHERE key LIKE 'usage:%' OR key LIKE 'public:llm:%'")]}
