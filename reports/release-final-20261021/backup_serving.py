"""Read serving corpus/config only into a new local backup; no conversations."""
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from landlaw.config import Settings
from landlaw.store import Store
from pydantic import SecretStr

OUT=Path(__file__).parent
target=Path('data/backups/before-final-20261021.json')
if target.exists():
    raise ValueError('Preserve existing backup')
settings=Settings().model_copy(update={'admin_database_url':SecretStr('')})
store=Store(settings)
try:
    size=store.rows('SELECT pg_database_size(current_database()) AS n')[0]['n']
    store.backup(target)
    payload=json.loads(target.read_text())
    assert set(payload)=={'format','releases','state'}
    active=next(r['value'] for r in payload['state'] if r['key']=='active_release')
    releases=[Store.decode_release(r['payload']) for r in payload['releases']]
    scopes={r['id']:sorted({d.get('project') or 'general' for d in r['documents']}) for r in releases}
    assert all(set(values)<={'ring4','general'} for values in scopes.values()), 'Do not restore a multi-project corpus'
    result={'checked_at':datetime.now(UTC).isoformat(),'status':'BACKUP_CREATED_RESTORE_PENDING',
        'scope':'Read-only serving corpus/config; no sessions/messages/traces/source_reviews.',
        'file':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,
        'active_corpus':active,'releases':scopes,'database_bytes':size,'serving_database_mutated':False,
        'contains_conversations':False,'restore_proof':None}
    (OUT/'before-deploy-backup.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:
    store.close()
