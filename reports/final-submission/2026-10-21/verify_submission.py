"""Verify this submission without models, network, credentials or DB access.

Writes only receipts in its own report folder. --prepare creates the initial
freeze manifest and the evidence-link index; it does not commit or deploy.
"""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

from landlaw.config import Settings
from landlaw.evaluation import configuration_fingerprint
from markdown_it import MarkdownIt
from pydantic import SecretStr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT / 'reports/phase3b-reliability-20261021T073924Z'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value, unicode=False):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=not unicode).encode()).hexdigest()


def source_files():
    names = subprocess.check_output(['git', 'ls-files', '-co', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    return {n: sha(ROOT/n) for n in sorted(set(names))
            if n and not n.startswith('reports/') and (ROOT/n).is_file()}


def references(markdown):
    for token in MarkdownIt().parse(markdown):
        for child in token.children or []:
            target = child.attrGet('href') if child.type == 'link_open' else child.attrGet('src') if child.type == 'image' else None
            if target:
                yield target


def slug(text):
    text = re.sub(r'[`*_]', '', text).strip().lower()
    text = ''.join(c for c in text if c.isalnum() or c in '-_ ')
    return text.replace(' ', '-')


def main(prepare=False):
    baseline = read(HERE/'baseline.json')
    prior = read(PRIOR/'release-manifest.json')
    files = source_files()
    changes = sorted(n for n in set(files) | set(baseline['source_files'])
                     if files.get(n) != baseline['source_files'].get(n))
    historical_changed = [n for n, value in baseline['historical_reports'].items()
                          if not (ROOT/n).is_file() or sha(ROOT/n) != value]
    settings = Settings(_env_file=None, database_url='', admin_database_url='', groq_api_key='', allow_stale_generation=False)
    sqlite_fp = configuration_fingerprint(settings)
    pg_fp = configuration_fingerprint(settings.model_copy(update={
        'database_url': SecretStr('postgresql://fingerprint-only/metadata')}))
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    receipts = {n: sha(ROOT/n) for n in prior['source_receipts_sha256']}
    suites = {n: sha(ROOT/n) for n in prior['evaluation_suites']}
    policy = canonical(read(ROOT/prior['source_policy']['path']), unicode=True)
    corpus_hash = sha(ROOT/prior['corpus']['path'])
    components = {'source_tree': canonical(files), 'runtime_sqlite': sqlite_fp,
        'runtime_pg_local': pg_fp, 'corpus_payload': corpus_hash, 'source_policy': policy,
        'receipt_bundle': canonical(receipts), 'evaluation_suites': suites,
        'serving_image': read(HERE/'serving-image-identity.json')['id']}
    mandatory = ['README.md','FINAL_PROJECT_REPORT.md','SLIDE_OUTLINE.md','DEMO_SCRIPT.md',
        'EVALUATION_SUMMARY.md','KNOWN_LIMITATIONS.md','RELEASE_CHECKLIST.md',
        'SUBMISSION_CHECKLIST.md','EVIDENCE_INDEX.md','CODE_FREEZE.md']
    if prepare:
        manifest = {'format': 1, 'phase': '4', 'prepared_at': datetime.now(UTC).isoformat(),
            'base_git_head': head, 'candidate_commit': None, 'working_tree_dirty': True,
            'source_tree_sha256': components['source_tree'], 'source_files_sha256': files,
            'phase3b_candidate_identity_sha256': prior['candidate_identity_sha256'],
            'candidate_identity_components': components, 'candidate_identity_sha256': canonical(components),
            'runtime': {**{k:v for k,v in prior['runtime'].items() if k != 'postgresql_fingerprint_planned_only'},
                'phase3b_postgresql_fingerprint_was_planned_only': True,
                'postgresql_fingerprint_local_verified': pg_fp, 'postgresql_cloud_verified': False},
            'corpus': prior['corpus'], 'source_policy': prior['source_policy'],
            'source_receipts_sha256': receipts, 'receipt_bundle_sha256': canonical(receipts),
            'evaluation_suites': suites, 'locks': read(HERE/'dependency-lock-check.json')['lock_files'],
            'phase4_core_changes_from_phase3b': changes,
            'docker': read(HERE/'docker-preflight.json'),
            'postgresql': {'receipt': 'postgres-preflight.json', 'sha256': sha(HERE/'postgres-preflight.json'),
                'scope': 'Isolated Docker PG16 only; not cloud or 19-case recall'},
            'carried_test_allocation': prior['existing_test_allocation'],
            'model_pilot_status': {'S06_historical': 'FAIL', 'C01_phase3a': 'INCOMPLETE',
                'C02_phase3a': 'NOT_RUN', 'C03_phase3a': 'NOT_RUN', 'final_runtime_model_inference': 'NOT_RUN'},
            'deployment_decision': 'NOT_READY', 'new_model_pilot_under_existing_allocation': 'NOT_READY',
            'academic_submission_status': 'DRAFT_FOR_REVIEW_NOT_FORMATTED_FINAL',
            'external_model_requests_phase4': 0, 'production_database_touched': False,
            'commit_push_deploy_performed': False,
            'limitations': ['No final-runtime model-answer pass or quality aggregate.',
                'No new candidate commit/CI/deployed image/public E2E.',
                'Source review 2026-10-21 does not establish 2026-10-23 applicability.',
                'Existing allocation insufficient for C02; no reset or unknown-usage refund.',
                'Local image/PG does not certify Supabase/cloud; developer test-tools layer is separate.']}
        path = HERE/'freeze-manifest.json'
        if path.exists():
            raise ValueError('Freeze exists; preserve it and validate without --prepare')
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
        entries = {}
        index_doc = (HERE/'EVIDENCE_INDEX.md').read_text()
        for link in references(index_doc):
            parsed = urlsplit(link)
            if parsed.scheme or not parsed.path:
                continue
            path = (HERE/unquote(parsed.path)).resolve()
            if path.is_file() and path.name not in {'validation.json', 'evidence-index.json'}:
                rel = str(path.relative_to(ROOT))
                entries[rel] = {'sha256': sha(path), 'bytes': path.stat().st_size}
        (HERE/'evidence-index.json').write_text(json.dumps({
            'format': 1, 'scope': 'Stable individual files directly linked from EVIDENCE_INDEX.md, excluding mutable validation and the index itself; no large copies. Directories are references, all prior report files protected by baseline.',
            'files': entries}, ensure_ascii=False, indent=2)+'\n')

    manifest = read(HERE/'freeze-manifest.json')
    pg_receipt = read(HERE/'postgres-preflight.json')
    checks = {'base_head_matches': head == baseline['head'] == manifest['base_git_head'],
        'source_set_matches_baseline': set(files) == set(baseline['source_files']),
        'only_packaging_core_delta': changes == ['.dockerignore'],
        'source_tree_matches_freeze': files == manifest['source_files_sha256'],
        'historical_reports_unchanged': not historical_changed,
        'sqlite_fingerprint_matches': sqlite_fp == prior['runtime']['sqlite_fingerprint_verified'],
        'pg_fingerprint_matches_local_receipt': pg_fp == pg_receipt['runtime_fingerprint'],
        'pg_backup_asset_matches_receipt': (ROOT/pg_receipt['backup_file']).is_file()
            and sha(ROOT/pg_receipt['backup_file']) == pg_receipt['backup_sha256'],
        'corpus_unchanged': corpus_hash == prior['corpus']['payload_sha256'],
        'source_policy_unchanged': policy == prior['source_policy']['canonical_sha256'],
        'receipt_bundle_unchanged': receipts == prior['source_receipts_sha256'] and canonical(receipts) == prior['receipt_bundle_sha256'],
        'locked_suites_unchanged': suites == prior['evaluation_suites'],
        'mandatory_documents_present': all((HERE/n).is_file() for n in mandatory),
        'image_runtime_matches': read(HERE/'image-probe.json')['sqlite_fingerprint'] == sqlite_fp,
        'model_never_called_phase4': manifest['external_model_requests_phase4'] == 0}
    recall = read(PRIOR/'retrieval-final/retrieval-recall-at5.json')
    rows = recall['rows']
    macro = sum(r['gold_hits']/r['gold_count'] for r in rows)/len(rows)
    hits, labels = sum(r['gold_hits'] for r in rows), sum(r['gold_count'] for r in rows)
    checks['recall_arithmetic_and_scope'] = (len(rows) == 19 and hits == 20 and labels == 21
        and abs(macro-recall['macro_recall_at_5']) < 1e-12
        and abs(hits/labels-recall['micro_recall_at_5']) < 1e-12
        and recall['runtime_fingerprint'] == sqlite_fp)
    links, errors = 0, []
    for document in sorted(HERE.glob('*.md')):
        for link in references(document.read_text()):
            parsed = urlsplit(link)
            if parsed.scheme or link.startswith('//'):
                continue
            path = (document.parent/unquote(parsed.path)).resolve() if parsed.path else document
            links += 1
            if not path.exists():
                errors.append({'document': document.name, 'target': link, 'reason': 'missing_file'})
            elif parsed.fragment and path.suffix == '.md':
                headings = {slug(line.lstrip('#').strip()) for line in path.read_text().splitlines() if re.match(r'^#{1,6} ', line)}
                if unquote(parsed.fragment) not in headings:
                    errors.append({'document': document.name, 'target': link, 'reason': 'missing_heading'})
    checks['markdown_local_links_exist'] = not errors
    index = read(HERE/'evidence-index.json')['files']
    index_mismatch = [n for n, row in index.items() if not (ROOT/n).is_file() or sha(ROOT/n) != row['sha256']]
    checks['evidence_index_hashes_match'] = not index_mismatch
    checks['lock_hashes_match'] = all(sha(ROOT/n) == value for n, value in manifest['locks'].items())
    output = {'status': 'PASS' if all(checks.values()) else 'FAIL',
        'checked_at': datetime.now(UTC).isoformat(), 'checks': checks,
        'source_files_checked': len(files), 'historical_report_files_checked': len(baseline['historical_reports']),
        'historical_changed': historical_changed, 'core_delta': changes,
        'local_links_checked': links, 'link_errors': errors, 'evidence_index_mismatches': index_mismatch,
        'scope': 'Offline hash/link/arithmetic validation, not a new legal review, inference, model quality, cloud/CI or deployment readiness check.',
        'external_model_requests': 0, 'production_database_touched': False}
    path = HERE/'validation.json'
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(output, ensure_ascii=False))
    return 0 if output['status'] == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    raise SystemExit(main(parser.parse_args().prepare))
