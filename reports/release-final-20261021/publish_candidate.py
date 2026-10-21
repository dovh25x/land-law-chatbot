"""Publish the checksum-verified candidate only AFTER safe code is serving.

Never migrates/drops/deletes. Staged receipts/policy are imported before the
atomic active pointer switch. A failure keeps old release data recoverable.
"""
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.publication import validate_corpus
from landlaw.store import Store
from pydantic import SecretStr

OUT=Path(__file__).parent
LEGAL=Path('reports/phase2c-current-20261021')
target=OUT/'corpus-publication.json'
if target.exists():
    raise ValueError('Preserve previous publication evidence')
rollback=json.loads((OUT/'rollback-restore.json').read_text())
assert rollback['status']=='PASS'
raw=Settings()
public='https://'+raw.public_hostname
with httpx.Client(timeout=60) as client:
    ready=client.get(public+'/readyz').json()
    status=client.get(public+'/api/v1/status').json()
assert ready.get('source_lookup_only') is True and status.get('generation_available') is False
settings=raw.model_copy(update={'app_env':'development','generation_enabled':False,'source_lookup_only':True,
    'allow_stale_generation':False,'database_url':raw.admin_database_url,'admin_database_url':SecretStr('')})
assert settings.database_url.get_secret_value()
assert ready.get('configuration_sha256')==configuration_fingerprint(settings)
source=Path('data/staging/phase2c-current/release-v5.json')
expected=json.loads(Path('reports/phase3b-reliability-20261021T073924Z/release-manifest.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected['corpus']['payload_sha256']
payload=json.loads(source.read_text())
validate_corpus(payload)
ident=payload['id']
class StagedStore(Store):
    def release(self,release_id=None,metadata_only=False):
        return super().release(release_id or ident,metadata_only)
store=StagedStore(settings)
try:
    old=store.state('active_release')
    assert old==rollback['active_corpus'], 'Serving pointer changed after rollback proof'
    if not store.release(ident,True):
        store.stage(payload)
    assert store.release(ident)['documents']==payload['documents']
    imported=[record_source_review(store,p) for p in sorted((LEGAL/'receipts-final').glob('*.json'))]
    activated=activate_source_gate(store,LEGAL/'source-gate-final.json')
    passages=[(d['id'],c['id'],c['checksum']) for d in payload['documents'] for c in d['chunks']]
    reviews=store.scoped_source_reviews(store.release(ident,True),passages,date(2026,10,21))
    count=sum(v=='fresh' for v in reviews.values())
    assert count==43 and store.source_gate_status(store.release(ident,True))['usable']
    store.publish(ident)
    assert store.state('active_release')==ident and store.state('previous_release')==old
    result={'status':'PASS','checked_at':datetime.now(UTC).isoformat(),'active_corpus':ident,'previous_release_retained':old,
        'payload_sha256':expected['corpus']['payload_sha256'],'receipt_count':len(imported),
        'source_gate':activated,'fresh_passages_as_of_2026_10_21':count,
        'safe_runtime_fingerprint':ready['configuration_sha256'],'generation_enabled':False,'source_lookup_only':True,
        'schema_migrated':False,'data_deleted':False,'credentials_changed':False,'external_llm_requests':0,
        'backup_and_local_restore_proof':'rollback-restore.json'}
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
finally:
    store.close()
