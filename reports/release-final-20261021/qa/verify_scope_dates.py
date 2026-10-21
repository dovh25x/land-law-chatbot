"""Replay receipt admission on a new private SQLite DB, without inference."""
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from landlaw.config import Settings
from landlaw.ops import activate_source_gate, record_source_review
from landlaw.store import Store

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT/'reports/phase2c-current-20261021'
DB = HERE/'source-scope-private.db'


def main():
    if DB.exists():
        raise ValueError('Preserve prior database; do not repeat this replay in place')
    settings = Settings(_env_file=None, app_env='development', database_url='', admin_database_url='',
                        groq_api_key='', sqlite_path=str(DB), allow_stale_generation=False)
    store = Store(settings)
    try:
        store.restore(ROOT/'reports/final-submission/2026-10-21/local-postgres-corpus-backup.json')
        release = store.release(None, True)
        before = store.source_gate_status(release)
        for receipt in sorted((SOURCE/'receipts-final').glob('*.json')):
            record_source_review(store, receipt)
        activate_source_gate(store, SOURCE/'source-gate-final.json')
        passages = {}
        receipt_missing_actual_chunk = []
        for receipt in sorted((SOURCE/'receipts-final').glob('*.json')):
            row = json.loads(receipt.read_text())
            for scope in row.get('verified_scope', []):
                for chunk_id, expected in scope['chunk_checksums'].items():
                    chunk = store.chunk(chunk_id, release['id'])
                    if chunk is None or chunk.checksum != expected:
                        receipt_missing_actual_chunk.append(chunk_id)
                    else:
                        passages[(row['document_id'], chunk_id)] = chunk.checksum
        rows = [(doc_id, chunk_id, checksum) for (doc_id, chunk_id), checksum in passages.items()]
        states = {day: store.scoped_source_reviews(release, rows, date.fromisoformat(day))
                  for day in ('2024-08-02', '2026-10-21', '2026-10-22', '2026-10-23')}
        counts = {day: dict(Counter(result.values())) for day, result in states.items()}
        # A historically reviewed Article 104 source is outside the current scope.
        item = store.chunk('luat-dat-dai-2024-104-1-0', release['id'])
        unreviewed_current = store.scoped_source_reviews(release,
            [(item.document_id, item.id, item.checksum)], date(2026, 10, 21))
        checks = {
            'restored_corpus_without_receipts_fails_closed': before['usable'] is False,
            'all_receipt_chunks_match_actual_snapshot': not receipt_missing_actual_chunk,
            'reviewed_current_passages_admitted': counts['2026-10-21'].get('fresh', 0) > 0,
            'reviewed_history_passages_admitted': counts['2024-08-02'].get('fresh', 0) > 0,
            'no_implicit_next_day_extension': counts['2026-10-22'].get('fresh', 0) == 0,
            'no_implicit_deadline_extension': counts['2026-10-23'].get('fresh', 0) == 0,
            'historical_only_article104_not_current': all(v != 'fresh' for v in unreviewed_current.values()),
        }
        output = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
                  'checked_at': datetime.now(UTC).isoformat(), 'storage_backend': 'private SQLite',
                  'corpus_id': release['id'], 'eligible_passages_union': store.source_gate_status(release),
                  'scope_date_state_counts': counts, 'actual_passages_checked': len(rows),
                  'missing_or_mismatching_receipt_chunks': receipt_missing_actual_chunk,
                  'unreviewed_current_article104': unreviewed_current,
                  'external_requests': 0, 'production_database_touched': False,
                  'scope': 'Exact chunk/date/source receipt admission only, not generated answers, semantic citation accuracy, model inference or legal review renewal.'}
        (HERE/'source-scope-date-verification.json').write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps(output, ensure_ascii=False))
        return 0 if all(checks.values()) else 1
    finally:
        store.close()


if __name__ == '__main__':
    raise SystemExit(main())
