"""Read the committed Git tree and local release asset; never mutate Git/DB.

This verifies clean-checkout *inputs* from Git objects without creating a
duplicate checkout or overwriting the academic exports. It is not a fresh OS
dependency install, cloud/CI run or a promise of byte-identical PDF metadata.
"""
import hashlib
import io
import json
import re
import subprocess
import argparse
from datetime import UTC, datetime
from pathlib import Path

from markdown_it import MarkdownIt

from landlaw.store import Store

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COMMIT = 'bc5c0e9c6df2fb72d6cd6aaa110e8cabbdddb9fb'
EXPECTED_TREE = 'deddd9d27614e30fe01fb47f7b3b852853c61d3aea6c0bb00e059950ecc307cb'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(final=False, output_name=None):
    commit = 'ec5d9a9d1f3f265ebd89f5c0524d41142b0806ec' if final else COMMIT
    expected_tree = '5b9b8af81fb3fa2f2f640a6b1053c365274716e5309d0dc21dd864247c4499ea' if final else EXPECTED_TREE
    final_freeze = json.loads((ROOT/'reports/release-final-20261021/candidate-final-freeze.json').read_text()) if final else None
    output_name = output_name or ('final-code-verification.json' if final else 'committed-release-verification.json')
    if Path(output_name).name != output_name:
        raise ValueError('Output must stay in the QA evidence folder')
    output = HERE/output_name
    if output.exists():
        raise ValueError('Preserve prior verification evidence: '+output_name)
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit], cwd=ROOT, text=True).splitlines()
    nameset = set(names)
    selected = [name for name in names if not name.startswith('reports/')]
    selected += [name for name in names if name.startswith('reports/submission-20261021/')]
    process = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT,
        input=''.join(commit+':'+name+'\n' for name in selected).encode(), stdout=subprocess.PIPE, check=True)
    content = io.BytesIO(process.stdout)
    committed = {}
    committed_markdown = {}
    for name in selected:
        header = content.readline().decode().strip().split()
        if len(header) != 3 or header[1] != 'blob':
            raise ValueError('Expected a committed blob: '+name)
        data = content.read(int(header[2]))
        assert content.read(1) == b'\n'
        committed[name] = hashlib.sha256(data).hexdigest()
        if name.startswith('reports/submission-20261021/') and name.endswith('.md'):
            committed_markdown[name] = data.decode()
    source = {name: committed[name] for name in sorted(selected) if not name.startswith('reports/')}
    source_sha = hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()
    source_mismatch = [name for name, expected in source.items() if sha(ROOT/name) != expected]
    docs_mismatch = [name for name in committed if name.startswith('reports/submission-20261021/')
                     and sha(ROOT/name) != committed[name]]
    baseline = json.loads((ROOT/'reports/final-submission/2026-10-21/baseline.json').read_text())
    historical_changed = [name for name, expected in baseline['historical_reports'].items()
                          if not (ROOT/name).exists() or sha(ROOT/name) != expected]
    freeze = json.loads((ROOT/'reports/final-submission/2026-10-21/freeze-manifest.json').read_text())
    gold_changed = [name for name, expected in freeze['evaluation_suites'].items() if sha(ROOT/name) != expected]
    suite_counts = {name: len((ROOT/name).read_text().splitlines()) for name in freeze['evaluation_suites']}
    receipt_changed = [name for name, expected in freeze['source_receipts_sha256'].items() if sha(ROOT/name) != expected]
    corpus_path = ROOT/('dist/final-corpus-release-20261021/corpus-backup.json' if final else 'dist/final-corpus-20261021/corpus-backup.json')
    asset = json.loads(corpus_path.read_text())
    releases = [Store.decode_release(row['payload']) for row in asset['releases']]
    candidate = next(row for row in releases if row['id'] == 'corpus-1afca764aa6692e0')
    original = json.loads((ROOT/'data/staging/phase2c-current/release-v5.json').read_text())
    counts = {'documents': len(candidate['documents']), 'chunks': sum(len(d['chunks']) for d in candidate['documents'])}
    forbidden_asset_keys = set(asset)-{'format', 'releases', 'state'}
    state_keys = [row['key'] for row in asset['state']]
    expected_assets = {'Final_Project_Report.pdf', 'Final_Project_Presentation.pdf',
                       'Final_Project_Presentation.pptx', 'architecture.png'}
    missing_links, asset_links = [], []
    for name in names:
        if not name.startswith('reports/submission-20261021/') or not name.endswith('.md'):
            continue
        for token in MarkdownIt().parse(committed_markdown[name]):
            for child in token.children or []:
                dest = child.attrGet('href') if child.type == 'link_open' else child.attrGet('src') if child.type == 'image' else None
                if not dest or re.match(r'^(https?:|mailto:|#)', dest):
                    continue
                target = (ROOT/name).parent/dest.split('#')[0]
                relative = str(target.resolve().relative_to(ROOT))
                if relative not in nameset:
                    if target.name in expected_assets:
                        asset_links.append({'document': name, 'target': relative})
                    else:
                        missing_links.append({'document': name, 'target': relative})
    build_prereqs = ['reports/submission-20261021/document-tools.txt',
                     'reports/submission-20261021/slides.json',
                     'reports/submission-20261021/delivery-status.json',
                     'reports/submission-20261021/Final_Project_Report.md',
                     'reports/submission-20261021/build_assets.py',
                     'reports/submission-20261021/export_pdf.cjs',
                     'reports/submission-20261021/validate_assets.py',
                     'docs/diagrams/architecture.svg', 'frontend/package-lock.json']
    checks = {'committed_source_tree_hash_matches': source_sha == expected_tree,
              'working_source_equals_committed_source': not source_mismatch,
              'committed_document_build_inputs_present': all(name in nameset for name in build_prereqs),
              'historical_artifacts_preserved': not historical_changed,
              'evaluation_gold_unchanged': not gold_changed and sorted(suite_counts.values()) == [4, 8, 20],
              'source_receipts_unchanged': not receipt_changed,
              'asset_checksum_matches': sha(corpus_path) == '1db94271217ef3765279a14a7609b09623b25c0fd3b8537f2ba99c674991160d',
              'asset_documents_exactly_match_original_candidate': candidate['documents'] == original['documents'],
              'asset_counts_match_candidate': counts == {'documents': 60, 'chunks': 7396},
              'asset_format_has_no_conversation_tables': asset['format'] == 1 and not forbidden_asset_keys,
              'no_missing_non_asset_document_links_in_git': not missing_links}
    core_delta = []
    if final:
        core_delta = subprocess.check_output(['git', 'diff', '--name-only', COMMIT, commit,
            '--', '.', ':(exclude)reports/'], cwd=ROOT, text=True).splitlines()
        checks['head_matches_final_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() == commit
        checks['candidate_final_freeze_matches_committed_source'] = final_freeze['source_files_sha256'] == source and final_freeze['source_tree_sha256'] == source_sha
        checks['only_expected_frontend_core_changes_after_bc5'] = sorted(core_delta) == [
            'frontend/e2e/navigation.spec.ts', 'frontend/e2e/source-lookup.spec.ts', 'frontend/src/App.tsx']
    receipt = {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checked_at': datetime.now(UTC).isoformat(),
               'commit': commit, 'source_tree_sha256': source_sha, 'source_files_checked': len(source),
               'core_changes_since_initial_source_only_release': core_delta,
               'freeze_reference': 'reports/release-final-20261021/candidate-final-freeze.json' if final else None,
               'committed_paths_total': len(names), 'checks': checks, 'source_mismatches': source_mismatch,
               'academic_documents_changed_after_commit': docs_mismatch,
               'document_links_checked_from': 'Committed Git blobs; live academic updates are listed separately and are not final-code defects',
               'historical_files_checked': len(baseline['historical_reports']),
               'historical_changed': historical_changed, 'gold_counts': suite_counts, 'gold_changed': gold_changed,
               'receipt_changed': receipt_changed, 'asset_counts': counts, 'asset_state_keys': state_keys,
               'asset_sha256': sha(corpus_path), 'missing_non_asset_document_links': missing_links,
               'expected_links_to_separate_generated_assets': asset_links,
               'clean_checkout_scope': 'Committed blob projection and required build-input presence. Full CI fresh checkout, dependency install and document re-export NOT RUN by QA; separate release assets and installed pinned tooling/Chromium/fonts are prerequisites. PDF metadata may differ on re-export.',
               'external_requests': 0, 'git_mutations': False, 'database_connections': 0}
    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('academic_documents_changed_after_commit','expected_links_to_separate_generated_assets')}, ensure_ascii=False))
    return 0 if all(checks.values()) else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final', action='store_true')
    parser.add_argument('--output-name')
    args = parser.parse_args()
    raise SystemExit(main(args.final, args.output_name))
