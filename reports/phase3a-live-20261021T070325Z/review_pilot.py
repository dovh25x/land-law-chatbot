"""Post-run review from saved evidence only. Never imports/calls a model provider."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    execution = json.loads((OUT / 'execution.json').read_text())
    lock = json.loads((OUT / 'configuration-lock.json').read_text())
    baseline = json.loads((OUT / 'baseline.json').read_text())
    corpus = json.loads(Path('data/staging/phase2c-current/release-v5.json').read_text())
    documents = {d['id']: d for d in corpus['documents']}
    cases = []
    for case in execution['cases']:
        rows = []
        for request_file in sorted((OUT / case['id']).glob('wire/*/request.json')):
            folder = request_file.parent
            request = json.loads(request_file.read_text())
            source = json.loads((folder / 'source-state.json').read_text())
            response = json.loads((folder / 'response.json').read_text())
            payload = json.loads(request['messages'][-1]['content'])
            ids = list(source['synthesis_sources'])
            aliases = {e['citation_id']: ident for e, ident in zip(payload['evidence'], ids)}
            content = response.get('body', {}).get('choices', [])
            draft = json.loads(content[0]['message']['content']) if content else None
            rows.append({
                'ordinal': int(folder.name), 'schema': source['schema'],
                'status_code': response.get('status_code'),
                'request_sha256': sha(request_file), 'response_sha256': sha(folder / 'response.json'),
                'request_saved_at_utc': datetime.fromtimestamp(request_file.stat().st_mtime, timezone.utc).isoformat(),
                'system_prompt_sha256': hashlib.sha256(request['messages'][0]['content'].encode()).hexdigest(),
                'wire_context_chars': len(json.dumps([payload['evidence'], payload['documents']],
                                                     ensure_ascii=False, separators=(',', ':'))),
                'retrieved_candidates': len(source['retrieved_sources']),
                'retained_count': len(source['retained_sources']), 'admitted_count': len(source['admitted_sources']),
                'synthesis_count': len(ids), 'aliases_to_source_ids': aliases,
                'required_evidence_checks': source['required_evidence_checks'],
                'all_required_evidence_present': all(r['present'] for r in source['required_evidence_checks']),
                'draft_citations_all_in_synthesis': (all(c in aliases for claim in draft['claims']
                    for c in claim['citation_ids']) if draft else None),
                'usage': response.get('usage', {}), 'latency_ms': response.get('latency_ms'),
                'rate_limit_headers': response.get('headers', {}),
                'reservation_tokens': source['reservation_tokens'],
                'sources': [{'alias': e['citation_id'], 'source_id': aliases[e['citation_id']],
                    'document_id': e['document_id'], 'locator': e['locator'],
                    'document_number': documents[e['document_id']]['document_number'],
                    'url': documents[e['document_id']]['url'],
                    'text_sha256': hashlib.sha256(e['text'].encode()).hexdigest()}
                    for e in payload['evidence']],
            })
        cases.append({'id': case['id'], 'result': 'INCOMPLETE',
            'attempt_started': case['attempt_started'], 'stop_reason': case['reason'],
            'wire_requests': case.get('wire_requests', 0), 'elapsed_ms': case.get('elapsed_ms'),
            'final_status': case.get('answer', {}).get('status'),
            'released_claims': case.get('answer', {}).get('verified_claims', []),
            'released_citations': case.get('answer', {}).get('citations', []), 'requests': rows})
    wait = ((OUT / 'C01/wire/03/request.json').stat().st_mtime
            - (OUT / 'C01/wire/02/response.json').stat().st_mtime)
    blocked = json.loads((OUT / 'C01/blocked-request.json').read_text())
    current_status = subprocess.check_output(['git', 'status', '--short'], text=True)
    filtered_status = ''.join(line + '\n' for line in current_status.splitlines()
                              if line != '?? reports/phase3a-live-20261021T070325Z/')
    protected = {str(p): sha(p) == checksum for p, checksum in lock['input_sha256'].items()}
    assert all(protected.values())
    assert all(sha(p) == h for p, h in baseline['phase2d_source_files'].items())
    assert filtered_status == baseline['status']
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    assert head == baseline['head']
    assert execution['budget']['wire_requests'] == 3
    assert execution['budget']['tokens_charged_including_unknown'] == 52159
    assert blocked['required_reservation'] + execution['budget']['tokens_charged_including_unknown'] > 60000
    assert wait >= 4
    review = {'reviewed_at': datetime.now(timezone.utc).isoformat(), 'phase': '3A',
        'decision_release_validation': 'NOT_READY', 'cases': cases, 'budget': execution['budget'],
        'blocked_next_request_reservation': blocked['required_reservation'],
        'would_charge_if_sent': blocked['required_reservation'] + execution['budget']['tokens_charged_including_unknown'],
        '429_retry_after_seconds': 4, 'observed_minimum_retry_wait_seconds': round(wait, 3),
        'budget_accounting_note': '4829 tokens are provider-reported. 52159 is a conservative bound including '
            'two full reservations for responses without usage, not measured consumption. A fourth request was '
            'blocked before network I/O. Runtime llm_calls=4 includes that blocked call; actual HTTP requests=3.',
        'C01_content_review': {
            'initial_draft': 'FAIL_NOT_RELEASABLE',
            'official_reference': '../phase2c-current-20261021/LEGAL_REVIEW.md',
            'citation_defect': 'Names NQ254/2025:3(10) but omits source C3 from claim citation_ids.',
            'scope_defects': [
                'Describes the insufficient-area support branch of Article111(4) without its material '
                'multi-generation/multiple-couple/shared-land and household-separation prerequisites.',
                'Extends the QD40 Article21(1) ward apartment/land-fund formulation without retaining the '
                'ward subject or distinct commune branch.',
            ],
            'OR_AND': 'The first draft uses non-annual-lease actor prerequisite AND certificate '
                '(OR land-allocation decision). No clear OR-to-AND collapse was observed there; '
                'this does not establish full answer correctness.',
            'structural_verifier': 'Rejected 0/1 supported. One issue requires explicit clause1 linkage '
                'wording, although the draft already names household/individual and non-annual lease. '
                'That issue alone does not prove a substantive subject error; the regex requires '
                'clause-number framing. Independent citation/scope defects remain. No F03 optimization performed.',
            'repair_result': 'UNKNOWN; HTTP429 then HTTP400 json_validate_failed, further retry blocked.',
            'abstention_classification': 'Operational budget interruption on an answerable case, not '
                'correct safe abstention. False Abstention Rate not computed for incomplete executions.',
        },
        'limitations': [
            'C02 and C03 never started after the first operational stop. Their 5070/6981-char contexts '
            'are Phase2D deterministic evidence only, not live-model captures in Phase3A.',
            'No model Verification API request completed; the initial verdict is the existing structural verifier.',
            'Visible successful response content is preserved; hidden reasoning is excluded. HTTP400 '
            'failed_generation payload is not preserved, only error metadata and full-body SHA256; '
            'the repair cannot be assessed or reconstructed.',
            'Only SQLite was used; PostgreSQL, cloud deployment and public E2E remain unverified here.',
            'Scoped legal review is fixed to 2026-10-21; it does not certify current law on 2026-10-23.',
        ],
        'identity': {'head': head, 'source_tree_sha256': lock['phase2d_source_tree_sha256'],
            'candidate_identity': lock['phase2d_candidate_identity'],
            'runtime_fingerprint': lock['runtime_fingerprint'], 'corpus_id': lock['corpus_id'],
            'corpus_sha256': lock['corpus_checksum'], 'model': lock['model'],
            'embedding': 'multilingual-e5-small-onnx-q8-window-v1', 'dimensions': 384},
        'preservation': {'head_unchanged': True, '199_source_files_unchanged': True,
            'locked_inputs_unchanged': all(protected.values()),
            'existing_working_tree_status_unchanged': True, 'only_new_phase3a_artifacts': True,
            'production_database_touched': False, 'S06': 'FAIL_UNCHANGED',
            'commit_push_deploy': False, 'full_evaluation': False, 'extra_judge': False},
        'offline_tests': {'command': '.venv/bin/python -m pytest -q '
            'reports/phase3a-live-20261021T070325Z/test_pilot_runner.py', 'passed': 8, 'failed': 0},
        'prior_backend_tests': {'passed': 486, 'source': 'Phase2D report only; not rerun in Phase3A'},
    }
    (OUT / 'technical-review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'cases': [{k: c[k] for k in ('id', 'result', 'wire_requests')}
                               for c in cases], 'preservation_checks': 'PASS',
                      'decision': review['decision_release_validation']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
