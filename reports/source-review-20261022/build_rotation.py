"""Rotate daily source-gate receipt windows after a successful mechanical recheck.

Derives new receipt JSONs from the byte-stable phase2c receipts-final set by
ONLY appending: a new verified_scope window 2026-10-22→2026-10-23 with the
identical chunk checksums (sources verified unchanged by recheck_sources.py),
today's re-fetch evidence, and an explicit mechanical-recheck review note.
Historical windows, relation review text and every other field stay
byte-preserved. Refuses to run unless recheck-access.json reports zero
failures. No database is touched here; the derived artifacts are replayed
and activated by apply_source_gate_20261022.py.
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent
OLD = Path('reports/phase2c-current-20261021')
NEW = BASE / 'receipts-20261022'
WINDOW = {'as_of_from': '2026-10-22', 'as_of_to': '2026-10-23'}
NOTE = (' Daily mechanical recheck 2026-10-22 (window 2026-10-22 to 2026-10-23): '
        'all pinned official source artifacts were re-fetched from their official '
        'URLs and every checksum/text snapshot matched the reviewed version '
        '(reports/source-review-20261022/recheck-access.json, recheck_sources.py). '
        'No amendment, document relationship or scope selection changed; the '
        'appended window reuses the identical recorded source passages.')


def receipt_hash(receipt):
    return hashlib.sha256(json.dumps(receipt, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def main():
    recheck = json.loads((BASE / 'recheck-access.json').read_text())
    failures = [r for r in recheck if r.get('status') != 200
                or (r.get('mode') == 'bytes' and r.get('checksum_match') is not True)
                or (r.get('mode') == 'text' and r.get('text_match') is not True)]
    if failures:
        raise SystemExit(f'Recheck has {len(failures)} failures; rotation refused')
    rechecked = {r['document_id'] for r in recheck}
    policy = json.loads((OLD / 'source-gate-final.json').read_text())
    assert policy['release_id'] == 'corpus-1afca764aa6692e0'
    NEW.mkdir(exist_ok=True)
    out_policy = json.loads(json.dumps(policy))
    report = {}
    for item in policy['receipts']:
        receipt = json.loads((OLD / 'receipts-final' / (item + '.json')).read_text())
        assert item in rechecked, f'{item} was not re-checked today'
        scopes = receipt['verified_scope']
        assert all(date.fromisoformat(s['as_of_from']) < date.fromisoformat(s['as_of_to']) for s in scopes)
        # Only receipts whose scope covers the current day block the public
        # chat on expiry; historical-only windows resolve on their own dates
        # and their checked_at remains fresh for 7 days, so they stay untouched.
        current = [s for s in scopes if s['as_of_to'] == '2026-10-22']
        if not current:
            report[item] = {'rotated': False, 'reason': 'historical-only windows; no current-day scope',
                            'unchanged_receipt_sha256': policy['receipts'][item]}
            out_policy['receipts'][item] = policy['receipts'][item]
            path = NEW / (item + '.json')
            path.write_text((OLD / 'receipts-final' / (item + '.json')).read_text())
            continue
        chunks = {}
        for scope in current:
            chunks.update(scope['chunk_checksums'])
        # Append-only window rotation: same immutable chunk checksums, new day.
        new_scope = {'as_of_from': WINDOW['as_of_from'], 'as_of_to': WINDOW['as_of_to'],
                     'chunk_checksums': chunks}
        receipt['verified_scope'].append(new_scope)
        evidence = [r for r in recheck if r['document_id'] == item]
        assert evidence
        # Preserve every original field byte-identically except checked_at,
        # which now records the fresh re-check issuance time.
        receipt['checked_at'] = max(r['checked_at'] for r in evidence)
        receipt.setdefault('review_evidence', []).extend(evidence)
        receipt['relation_review'] = receipt.get('relation_review', '') + NOTE
        path = NEW / (item + '.json')
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        out_policy['receipts'][item] = receipt_hash(receipt)
        report[item] = {'previous_receipt_sha256': policy['receipts'][item],
                        'new_receipt_sha256': out_policy['receipts'][item],
                        'window': [WINDOW['as_of_from'], WINDOW['as_of_to']],
                        'chunks': len(new_scope['chunk_checksums']),
                        'checked_at': receipt['checked_at'],
                        'recheck_artifacts': len(evidence)}
    (BASE / 'source-gate-20261022.json').write_text(json.dumps(out_policy, ensure_ascii=False, indent=2) + '\n')
    (BASE / 'rotation-report.json').write_text(json.dumps(
        {'created_at': max(r['checked_at'] for r in recheck), 'release_id': policy['release_id'],
         'recheck_records': len(recheck), 'receipts': report,
         'policy_sha256': receipt_hash(out_policy),
         'scope': 'Mechanical window rotation of unchanged sources; review of identical checksums from 2026-10-20/21 remains attached.'},
        ensure_ascii=False, indent=2) + '\n')
    print('receipt hashes:', {k: v[:12] for k, v in out_policy['receipts'].items()})
    print('policy sha256:', receipt_hash(out_policy)[:12])
    return 0


if __name__ == '__main__':
    sys.exit(main())
