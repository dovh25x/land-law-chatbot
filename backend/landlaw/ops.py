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
    if not receipt.get('relation_review') or not receipt.get('evidence_urls') or not all(official_url(url) for url in receipt['evidence_urls']):
        raise ValueError('Require source evidence URLs and explicit amendment/transition review')
    encoded=json.dumps(receipt,ensure_ascii=False,sort_keys=True)
    ident=hashlib.sha256(encoded.encode()).hexdigest()
    with store.transaction() as conn:
        store.execute(conn,'INSERT INTO source_reviews VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',
            (ident,release['id'],doc['id'],doc['checksum'],checked.isoformat(),receipt['status'],encoded))
    return {'receipt_sha256':ident,'document_id':doc['id'],'status':receipt['status']}


def status(store):
    release=store.release(None,True)
    cutoff=(utcnow()-timedelta(hours=1)).isoformat()
    turns=store.rows('SELECT status,COUNT(*) AS count FROM turns WHERE created_at>? GROUP BY status',(cutoff,))
    failed=sum(r['count'] for r in turns if r['status'] in {'error','expired'})
    return {'checked_at':utcnow().isoformat(),'database':store.ready(),'corpus':(release or {}).get('id'),
        'sources_fresh':bool(release) and store.source_fresh(release),'generation_enabled':store.settings.generation_enabled,
        'provider_cooldown_seconds':store.cooldown(),'last_hour_turns':{r['status']:r['count'] for r in turns},
        'needs_attention':failed>=5 or not release or not store.source_fresh(release),
        'usage':[{'kind':r['key'],'units':r['value']} for r in store.rows("SELECT key,value FROM counters WHERE key LIKE 'usage:%' OR key LIKE 'public:llm:%'")]}
