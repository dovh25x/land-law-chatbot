"""Bind offline evidence to the final source tree without editing old artifacts."""
import difflib
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pydantic import SecretStr
from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint

OUT = Path(__file__).parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


baseline = json.loads((OUT / 'baseline.json').read_text())
old = json.loads(Path('reports/phase2d-synthesis-20261021/release-manifest.json').read_text())
changed = [p for p, h in baseline['source_files_before'].items() if sha(p) != h]
assert sorted(changed) == ['backend/landlaw/evaluation.py', 'backend/landlaw/provider.py',
                           'scripts/evaluate_generation_candidate.py']
assert all(Path(p).is_file() and sha(p) == h for p, h in baseline['historical_report_sha256'].items())
assert all(sha(p) == h for p, h in baseline['protected_inputs'].items())
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert head == baseline['head']
paths = subprocess.check_output(['git', 'ls-files', '-co', '--exclude-standard', '-z'], text=True).split('\0')
sources = {p: sha(p) for p in sorted(set(paths)) if p and not p.startswith('reports/') and Path(p).is_file()}
source_tree = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
save('source-files-sha256.json', sources)
patch = ''
for path in changed:
    before = OUT / 'source-before' / path
    patch += ''.join(difflib.unified_diff(before.read_text().splitlines(True),
        Path(path).read_text().splitlines(True), fromfile='before/' + path, tofile='after/' + path))
for path in ['backend/landlaw/request_budget.py', 'tests/test_request_budget.py']:
    patch += ''.join(difflib.unified_diff([], Path(path).read_text().splitlines(True),
        fromfile='/dev/null', tofile='after/' + path))
(OUT / 'phase3b-only.patch').write_text(patch)
settings = Settings(_env_file=None, app_env='development', database_url='', admin_database_url='',
                    groq_api_key='', allow_stale_generation=False)
runtime = configuration_fingerprint(settings)
pg_planned = configuration_fingerprint(settings.model_copy(update={'database_url': SecretStr('postgresql://isolated')}))
capture = json.loads((OUT / 'synthesis-final/report.json').read_text())
retrieval = json.loads((OUT / 'retrieval-final/retrieval-recall-at5.json').read_text())
startup = json.loads((OUT / 'startup-and-positive-fixture-final.json').read_text())
assert runtime == capture['runtime_fingerprint'] == retrieval['runtime_fingerprint'] == startup['ready']['configuration_sha256']
assert capture['inputs_unchanged'] and capture['runtime_unchanged']
counts = re.search(r'(\d+) passed', (OUT / 'backend-tests-final-2.log').read_text())
assert counts and int(counts[1]) == 516
assert '100 passed' in (OUT / 'frontend-e2e.log').read_text()
assert 'Tests  14 passed' in (OUT / 'frontend-tests.log').read_text()
assert 'built in' in (OUT / 'frontend-build.log').read_text()
suites = {p: sha(p) for p in old['evaluation_suites']}
assert suites == old['evaluation_suites']
receipt_files = {str(p): sha(p) for p in sorted(Path('reports/phase2c-current-20261021/receipts-final').glob('*.json'))}
receipt_bundle = hashlib.sha256(json.dumps(receipt_files, sort_keys=True).encode()).hexdigest()
corpus = sha('data/staging/phase2c-current/release-v5.json')
assert corpus == old['corpus']['payload_sha256']
components = {'source_tree': source_tree, 'runtime_sqlite': runtime,
              'runtime_pg_planned_only': pg_planned, 'corpus_payload': corpus,
              'source_policy': old['source_policy']['canonical_sha256'],
              'receipt_bundle': receipt_bundle, 'evaluation_suites': suites}
candidate = hashlib.sha256(json.dumps(components, sort_keys=True).encode()).hexdigest()
coverage = json.loads((OUT / 'coverage-preflight/report.json').read_text())
budget = json.loads((OUT / 'prior-allocation-check.json').read_text())
assert budget['runtime_fingerprint_for_proposed_request'] == runtime
assert not budget['request_allowed_under_carried_budget']
quote = startup['quote_fixture']
assert quote['answer']['status'] == 'answered'
assert quote['all_released_citations_reviewed'] and quote['all_released_citations_in_snapshot']
selected = {c['id']: c for c in capture['cases']}
assert all(selected[key]['complete'] for key in ['C02', 'C03'])
manifest = {'format': 1, 'phase': '3B', 'prepared_at': datetime.now(timezone.utc).isoformat(),
    'decision_new_model_pilot_with_existing_allocation': 'NOT_READY',
    'runtime_offline_preflight': 'PARTIAL_LEGACY_FIXTURE_FAILURES_AND_NO_POSTGRESQL',
    'deployment_decision': 'NOT_READY', 'candidate_commit': None, 'git_head': head,
    'working_tree_dirty': True, 'source_tree_sha256': source_tree,
    'candidate_identity_components': components, 'candidate_identity_sha256': candidate,
    'runtime': {'sqlite_fingerprint_verified': runtime, 'postgresql_fingerprint_planned_only': pg_planned,
        'llm_model': settings.generation_model, 'llm_provider': settings.llm_provider,
        'embedding_contract': old['runtime']['embedding_contract'],
        'allow_stale_generation': False, 'max_requests_per_turn': 6, 'max_tools': 12,
        'retrieval_rounds': 2, 'repairs': 1, 'turn_seconds': 90,
        'max_completion_tokens': 2048, 'format_failures_per_generate_max': 2},
    'corpus': {**old['corpus'], 'modified_in_phase3b': False},
    'source_policy': {**old['source_policy'], 'modified_in_phase3b': False},
    'source_receipts_sha256': receipt_files, 'receipt_bundle_sha256': receipt_bundle,
    'evaluation_suites': suites, 'prior_manifest_sha256': sha('reports/phase2d-synthesis-20261021/release-manifest.json'),
    'checks': {'backend_passed': 516, 'new_accounting_and_reliability_regressions': 30,
        'frontend_unit_passed': 14, 'frontend_build': 'PASS', 'playwright_fixture_passed': 100,
        'postgresql': 'NOT_RUN_NO_LOCAL_SERVICE_REMOTE_NOT_TOUCHED',
        'health_status': startup['health_status'], 'offline_ready_status': startup['ready_status'],
        'offline_ready503_reason': 'Empty API key intentional; no real provider connectivity test',
        'source_gate_usable': startup['source_gate_usable'], 'whole_corpus_verified': False,
        'positive_source_quote_fixture': 'PASS_NOT_MODEL',
        'legacy_coverage_fixture_status_matches': sum(c['status_matches'] for c in coverage['cases']),
        'legacy_coverage_fixture_cases': len(coverage['cases']),
        'legacy_coverage_fixture_failures': [c['id'] for c in coverage['cases'] if not c['status_matches']],
        'context_complete': {key: {'required_units': len(selected[key]['source_requirements']),
            'wire_context_chars': selected[key]['wire_context_chars'], 'complete': selected[key]['complete']}
            for key in ('C02', 'C03')},
        'local_backup_restore': coverage['restore'],
        'retrieval': {k: retrieval[k] for k in ('storage_backend', 'eligible_cases', 'gold_label_denominator',
            'gold_hits_at_5', 'macro_recall_at_5', 'micro_recall_at_5')},
        'external_model_requests_this_phase': 0, 'S06': 'FAIL_UNCHANGED'},
    'existing_test_allocation': budget,
    'limitations': ['No legal prompt/verifier/source/corpus changes; answer quality is unmeasured on final runtime.',
        'No proven smaller GPT-OSS token upper bound; conservative byte/framing reservations retained.',
        'No automatic new allocation or refund of prior errors missing provider usage.',
        'Legacy C02/C03 fixtures still rejected for citations outside actual synthesis snapshot; gold/fixtures unchanged.',
        'No PostgreSQL integration, public E2E or deployed-fingerprint verification.',
        'Current legal scope is 2026-10-21; no receipt extended to 2026-10-23.']}
save('release-manifest.json', manifest)
save('preservation.json', {'head_unchanged': True, 'historical_report_files_checked': len(baseline['historical_report_sha256']),
    'historical_reports_unchanged': True, 'gold_and_corpus_unchanged': True,
    'modified_existing_source_files': changed,
    'new_source_files': ['backend/landlaw/request_budget.py', 'tests/test_request_budget.py'],
    'all_other_existing_source_files_unchanged': True,
    'agent_synthesis_verifier_and_F01_source_gate_files_unchanged': True,
    'new_source_file_count': len(sources), 'source_tree_sha256': source_tree,
    'no_commit_push_deploy': True, 'no_production_or_cloud_database_operations': True})
print(json.dumps({'runtime_fingerprint': runtime, 'source_tree_sha256': source_tree,
    'candidate_identity_sha256': candidate, 'source_files': len(sources),
    'protected_historical_reports': len(baseline['historical_report_sha256']),
    'model_pilot_existing_allocation': 'NOT_READY'}, indent=2))
