"""Operator-only metadata commands. Never archive or expose conversation bodies."""
import hashlib
import json
from datetime import datetime, timedelta
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


def activate_source_gate(store, policy_path: Path):
    """Pin an operator-reviewed receipt set without changing source content."""
    policy = json.loads(policy_path.read_text())
    release = store.release(None, True)
    if (policy.get('version') != 1 or not release or policy.get('release_id') != release['id']
            or not isinstance(policy.get('receipts'), dict) or not policy['receipts']):
        raise ValueError('Source gate requires an active release and pinned receipt set')
    for doc_id, ident in policy['receipts'].items():
        rows = store.rows('SELECT document_id,checksum,receipt FROM source_reviews WHERE id=? AND release_id=?',
                          (ident, release['id']))
        doc = next((d for d in release['documents'] if d['id'] == doc_id), None)
        if (not rows or rows[0]['document_id'] != doc_id or not doc
                or rows[0]['checksum'] != doc['checksum']
                or not json.loads(rows[0]['receipt']).get('verified_scope')):
            raise ValueError('Source gate requires imported checksum-bound scoped receipts')
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
    return {'checked_at':utcnow().isoformat(),'database':store.ready(),'corpus':(release or {}).get('id'),
        'sources_fresh':fresh,'generation_enabled':store.settings.generation_enabled,
        'source_gate':gate,
        'allow_stale_generation':store.settings.allow_stale_generation,
        'warnings':[] if fresh else ['source_stale'],
        'provider_cooldown_seconds':store.cooldown(),'last_hour_turns':{r['status']:r['count'] for r in turns},
        'needs_attention':failed>=5 or not release or not sources_available,
        'usage':[{'kind':r['key'],'units':r['value']} for r in store.rows("SELECT key,value FROM counters WHERE key LIKE 'usage:%' OR key LIKE 'public:llm:%'")]}
