"""Offline read-only candidate checks; write a receipt only below this folder."""
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PHASE4 = ROOT / 'reports/final-submission/2026-10-21'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mismatch(rows):
    return [name for name, expected in rows.items()
            if not (ROOT/name).is_file() or sha(ROOT/name) != expected]


def main():
    freeze = read(PHASE4/'freeze-manifest.json')
    baseline = read(PHASE4/'baseline.json')
    historical_changes = mismatch(baseline['historical_reports'])
    source_changes = mismatch(freeze['source_files_sha256'])
    phase4_seal_mismatches = []
    seal_count = 0
    for line in (PHASE4/'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        seal_count += 1
        if not (PHASE4/name).is_file() or sha(PHASE4/name) != expected:
            phase4_seal_mismatches.append(name)
    suites_changed = mismatch(freeze['evaluation_suites'])
    receipts_changed = mismatch(freeze['source_receipts_sha256'])
    locks_changed = mismatch(freeze['locks'])
    recall = read(ROOT/'reports/phase3b-reliability-20261021T073924Z/retrieval-final/retrieval-recall-at5.json')
    rows = recall['rows']
    hits, gold = sum(x['gold_hits'] for x in rows), sum(x['gold_count'] for x in rows)
    macro = sum(x['gold_hits']/x['gold_count'] for x in rows)/len(rows)
    settings = Settings(_env_file=None, database_url='', admin_database_url='', groq_api_key='', allow_stale_generation=False)
    fingerprint = configuration_fingerprint(settings)
    policy = read(ROOT/freeze['source_policy']['path'])
    policy_sha = hashlib.sha256(json.dumps(policy, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    checks = {
        'phase4_source_bytes_unchanged': not source_changes,
        'all_prior_historical_reports_unchanged': not historical_changes,
        'sealed_phase4_files_unchanged': not phase4_seal_mismatches,
        'evaluation_gold_suites_unchanged': not suites_changed,
        'source_receipts_unchanged': not receipts_changed,
        'dependency_deploy_locks_unchanged': not locks_changed,
        'corpus_payload_unchanged': sha(ROOT/freeze['corpus']['path']) == freeze['corpus']['payload_sha256'],
        'source_policy_unchanged': policy_sha == freeze['source_policy']['canonical_sha256'],
        'runtime_fingerprint_matches_final_sqlite': fingerprint == freeze['runtime']['sqlite_fingerprint_verified'],
        'recall_scope_arithmetic': len(rows) == 19 and hits == 20 and gold == 21
            and abs(macro-recall['macro_recall_at_5']) < 1e-12,
    }
    receipt = {
        'checked_at': datetime.now(UTC).isoformat(),
        'status': 'PASS' if all(checks.values()) else 'FAIL',
        'checks': checks,
        'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'source_files_checked': len(freeze['source_files_sha256']),
        'historical_files_checked': len(baseline['historical_reports']),
        'phase4_seal_files_checked': seal_count,
        'mismatches': {'source': source_changes, 'history': historical_changes,
                       'phase4_seal': phase4_seal_mismatches, 'suites': suites_changed,
                       'receipts': receipts_changed, 'locks': locks_changed},
        'runtime_fingerprint': fingerprint,
        'corpus_sha256': freeze['corpus']['payload_sha256'],
        'source_policy_sha256': policy_sha,
        'recall': {'backend': 'SQLite', 'cases': len(rows), 'gold_hits': hits,
                   'gold_count': gold, 'macro': macro, 'micro': hits/gold,
                   'scope': 'Existing offline retrieval only; not answer correctness or new run'},
        'source_scope_date': freeze['source_policy']['scope_date'],
        'external_requests': 0,
        'production_database_touched': False,
        'scope': 'Read-only source, receipt, corpus, historical evidence and arithmetic verification; no API, database connection, inference, deployment, CI or browser claim.',
    }
    (HERE/'candidate-verification.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
