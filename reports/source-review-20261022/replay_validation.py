"""Offline replay of the 2026-10-22 receipt rotation on an isolated SQLite store.

Proves, before any production write: (1) the blocker reproduces with the old
gate (as_of=2026-10-22 -> unknown), (2) after recording the rotated receipts
and activating source-gate-20261022.json every pinned current-day chunk is
fresh at as_of=2026-10-22, (3) historical windows still resolve, and
(4) the previous 2026-10-21 window still resolves. No LLM, no network, no prod.
"""
import json
import tempfile
from datetime import date
from pathlib import Path

from landlaw.config import Settings
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.store import Store

BASE = Path(__file__).resolve().parent
BACKUP = Path('reports/phase3b-reliability-20261021T073924Z/local-corpus-backup.json')
POLICY = BASE / 'source-gate-20261022.json'
ROTATED = ['luat-thu-do-2026', 'nd-226-2025', 'qd-40-2026-hanoi',
           'luat-dat-dai-2024', 'nd-49-2026', 'nq-254-2025', 'nd-88-2024']
PILOT_CHUNKS = {'qd-40-2026-hanoi-9-1-1': 'qd-40-2026-hanoi',
                'luat-dat-dai-2024-106-1-0': 'luat-dat-dai-2024'}


def load_receipt(doc_id):
    return json.loads((BASE / 'receipts-20261022' / (doc_id + '.json')).read_text())


def scope_with(receipt, as_of_from=None, as_of_to=None):
    for scope in receipt['verified_scope']:
        if (as_of_from is None or scope['as_of_from'] == as_of_from) and \
           (as_of_to is None or scope['as_of_to'] == as_of_to):
            return scope
    raise AssertionError(f'no matching scope in {receipt["document_id"]}')


def probe(store, release, doc_id, scope, as_of):
    states = store.scoped_source_reviews(release, [(doc_id, c, k) for c, k in scope['chunk_checksums'].items()], as_of)
    return sorted(set(states.values()))


with tempfile.TemporaryDirectory(prefix='landlaw-rotation-') as folder:
    settings = Settings(_env_file=None, app_env='development', database_url='',
                        admin_database_url='', groq_api_key='',
                        sqlite_path=str(Path(folder) / 'rotation.db'), allow_stale_generation=False)
    store = Store(settings)
    try:
        store.restore(BACKUP)
        release = store.release(None, True)
        assert release['id'] == 'corpus-1afca764aa6692e0', release['id']
        policy = json.loads(POLICY.read_text())
        today = date.fromisoformat('2026-10-22')
        yesterday = date.fromisoformat('2026-10-21')

        # 1. Blocker reproduces with the old (not yet rotated) gate state.
        before = {}
        for doc_id in ROTATED:
            scope = scope_with(load_receipt(doc_id), '2026-10-22', '2026-10-23')
            before[doc_id] = probe(store, release, doc_id, scope, today)
        assert all(v == ['unknown'] for v in before.values()), before

        # 2. Apply the rotation and activate the new gate.
        records = [record_source_review(store, BASE / 'receipts-20261022' / (doc_id + '.json'))
                   for doc_id in policy['receipts']]
        activated = activate_source_gate(store, POLICY)
        gate = store.source_gate_status(release)
        assert gate['usable'], gate

        # 3. Every pinned current-day chunk is fresh at as_of=2026-10-22.
        after = {}
        for doc_id in ROTATED:
            scope = scope_with(load_receipt(doc_id), '2026-10-22', '2026-10-23')
            after[doc_id] = probe(store, release, doc_id, scope, today)
        assert all(v == ['fresh'] for v in after.values()), after

        # 4. Pilot chunks fresh at as_of=2026-10-22.
        chunk_map = {}
        for chunk_id, doc_id in PILOT_CHUNKS.items():
            chunk_map[(doc_id, chunk_id)] = scope_with(load_receipt(doc_id), '2026-10-22', '2026-10-23')['chunk_checksums'][chunk_id]
        pilot = store.scoped_source_reviews(release, [(d, c, k) for (d, c), k in chunk_map.items()], today)
        assert set(pilot.values()) == {'fresh'}, pilot

        # 5. Historical windows still resolve on their own dates.
        historical = {}
        history = {'luat-43-2024': '2024-12-01', 'nd-151-2025': '2025-07-15',
                   'qd-10-2026-hanoi': '2026-01-25', 'nd-88-2024': '2024-09-01'}
        for doc_id, as_of in history.items():
            receipt = load_receipt(doc_id)
            matched = next(s for s in receipt['verified_scope'] if s['as_of_from'] <= as_of < s['as_of_to'])
            historical[doc_id] = probe(store, release, doc_id, matched, date.fromisoformat(as_of))
        assert all(v == ['fresh'] for v in historical.values()), historical

        # 6. The previous 2026-10-21 window still resolves (history preserved).
        preserved = {}
        for doc_id in ROTATED:
            receipt = load_receipt(doc_id)
            scope = next((s for s in receipt['verified_scope'] if s['as_of_to'] == '2026-10-22'), None)
            if scope:
                preserved[doc_id] = probe(store, release, doc_id, scope, yesterday)
        assert all(v == ['fresh'] for v in preserved.values()), preserved

        report = {'corpus_id': release['id'],
                  'before_rotation_2026_10_22': before, 'receipts': records,
                  'activation': activated, 'gate': gate,
                  'after_rotation_2026_10_22': after,
                  'pilot_chunks_2026_10_22': {c: pilot[f"{PILOT_CHUNKS[c]}:{c}"] for c in PILOT_CHUNKS},
                  'historical_windows': historical,
                  'previous_window_2026_10_21': preserved}
        (BASE / 'replay-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'gate_usable': gate['usable'], 'fresh_docs': list(after),
                          'pilot': report['pilot_chunks_2026_10_22'],
                          'historical': historical, 'previous_window': preserved}, ensure_ascii=False))
    finally:
        store.close()
