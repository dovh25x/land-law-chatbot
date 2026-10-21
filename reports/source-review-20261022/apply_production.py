"""Apply the validated 2026-10-22 source-gate rotation to the production database.

Uses the owner connection only for additive source_review inserts and the
gate state pointer. Never creates schemas, drops data, or changes the corpus.
Refuses to run if the active release or the pinned old receipts changed, or
if the offline replay validation was not green.
"""
import json
from datetime import date
from pathlib import Path

from landlaw.config import Settings
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.store import Store
from pydantic import SecretStr
from datetime import UTC, datetime

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'reports/source-review-20261022'
OLD = ROOT / 'reports/phase2c-current-20261021'
PILOT = [('qd-40-2026-hanoi', 'qd-40-2026-hanoi-9-1-1'),
         ('luat-dat-dai-2024', 'luat-dat-dai-2024-106-1-0')]

replay = json.loads((BASE / 'replay-validation.json').read_text())
assert replay['gate']['usable'] and set(replay['pilot_chunks_2026_10_22'].values()) == {'fresh'}

raw = Settings()
assert raw.admin_database_url.get_secret_value()
settings = raw.model_copy(update={'database_url': raw.admin_database_url, 'admin_database_url': SecretStr('')})
policy_new = json.loads((BASE / 'source-gate-20261022.json').read_text())
policy_old = json.loads((OLD / 'source-gate-final.json').read_text())

store = Store(settings)
evidence = {}
try:
    release = store.release(None, True)
    assert release['id'] == 'corpus-1afca764aa6692e0', release['id']
    documents_before = [d['checksum'] for d in release['documents']]
    gate_before = store.source_gate_status(release)

    records = []
    for doc_id in policy_new['receipts']:
        records.append({**record_source_review(store, BASE / 'receipts-20261022' / (doc_id + '.json')),
                        'rotated': policy_new['receipts'][doc_id] != policy_old['receipts'][doc_id]})
    activated = activate_source_gate(store, BASE / 'source-gate-20261022.json')
    gate_after = store.source_gate_status(release)
    documents_after = [d['checksum'] for d in store.release(None, True)['documents']]
    assert documents_after == documents_before

    # Live pilot probe at today's Hanoi date through the real production rows.
    pilot_states = {}
    for doc_id, chunk_id in PILOT:
        receipt = json.loads((BASE / 'receipts-20261022' / (doc_id + '.json')).read_text())
        chunk_checksum = next(s for s in receipt['verified_scope'] if s['as_of_to'] == '2026-10-23')['chunk_checksums'][chunk_id]
        states = store.scoped_source_reviews(release, [(doc_id, chunk_id, chunk_checksum)], date(2026, 10, 22))
        pilot_states[chunk_id] = states.get(f'{doc_id}:{chunk_id}')
        assert pilot_states[chunk_id] == 'fresh', pilot_states
    assert gate_after['usable'], gate_after
    evidence = {'status': 'PASS', 'applied_at': datetime.now(UTC).isoformat(),
                'release_id': release['id'], 'documents_unchanged': True,
                'gate_before': gate_before, 'gate_after': gate_after,
                'activation': activated, 'receipts': records,
                'pilot_states_2026_10_22': pilot_states,
                'data_deleted': False, 'schema_changed': False, 'release_changed': False,
                'external_llm_requests': 0,
                'scope': 'Owner-role additive receipt rotation and gate pointer update only.'}
    (BASE / 'apply-production.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': 'PASS', 'release_id': release['id'], 'gate_after': gate_after,
                      'rotated': [r['document_id'] for r in records if r['rotated']],
                      'pilot': pilot_states}, ensure_ascii=False))
finally:
    store.close()
