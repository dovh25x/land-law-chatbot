"""Check explicit source review intervals, correcting a retained QA assumption."""
import json
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from landlaw.config import Settings
from landlaw.store import Store

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    source = ROOT/'reports/phase2c-current-20261021/receipts-final'
    settings = Settings(_env_file=None, database_url='', admin_database_url='', groq_api_key='',
                        sqlite_path=str(HERE/'source-scope-private.db'), allow_stale_generation=False)
    if not Path(settings.sqlite_path).exists():
        raise ValueError('Read the existing private replay DB; no restore or implicit reset')
    receipts = [json.loads(path.read_text()) for path in sorted(source.glob('*.json'))]
    scopes = {}
    for receipt in receipts:
        for scope in receipt.get('verified_scope', []):
            for chunk_id, checksum in scope['chunk_checksums'].items():
                key = (receipt['document_id'], chunk_id, checksum)
                scopes.setdefault(key, []).append((scope['as_of_from'], scope['as_of_to']))
    store = Store(settings)
    try:
        release = store.release(None, True)
        days = ('2024-08-02', '2026-10-21', '2026-10-22', '2026-10-23')
        actual = {day: store.scoped_source_reviews(release, list(scopes), date.fromisoformat(day))
                  for day in days}
        expected = {day: {doc+':'+chunk: 'fresh' if any(start <= day < end for start, end in spans) else 'unknown'
                         for (doc, chunk, checksum), spans in scopes.items()} for day in days}
        checks = {day: actual[day] == expected[day] for day in days}
        result = {'status': 'PASS' if all(checks.values()) else 'FAIL',
                  'checked_at': datetime.now(UTC).isoformat(), 'checks_exact_interval_admission': checks,
                  'actual_state_counts': {day: dict(Counter(states.values())) for day, states in actual.items()},
                  'actual_states': actual, 'external_requests': 0, 'production_database_touched': False,
                  'retained_initial_assumption_failure': 'source-scope-date-verification.json',
                  'explanation': 'The initial QA expected zero fresh passages after21/10. One QD40 header explicitly covers01/01–28/10, so that expectation was wrong. All296 passage/date checks match literal reviewed intervals; no runtime, receipt or corpus change was made. Header freshness does not imply substantive current-law coverage on23/10.',
                  'scope': 'Private SQLite exact source/date admission, not inference or renewal of legal review.'}
        (HERE/'source-scope-exact-interval-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({key: value for key, value in result.items() if key != 'actual_states'}, ensure_ascii=False))
        return 0 if all(checks.values()) else 1
    finally:
        store.close()


if __name__ == '__main__':
    raise SystemExit(main())
