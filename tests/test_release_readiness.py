"""Release approval must be recomputed from frozen, checksum-bound evidence."""
import hashlib
import json

import pytest
from landlaw.evaluation import configuration_fingerprint, dataset
from landlaw.security import utcnow
from pydantic import SecretStr

from scripts.check_release_readiness import model_gate, require_ready


def natural_report(candidate, settings):
    from pathlib import Path
    path = Path('data/evaluation/natural.jsonl')
    doc = candidate['documents'][0]
    chunk = doc['chunks'][0]
    rows = []
    for case in dataset(path):
        # Only test evidence plumbing and thresholds. These synthetic test
        # reviews are never saved as a model run or a legal-quality result.
        substantive = bool(case.get('gold_chunk_ids'))
        citation = {'id': chunk['id'], 'document_id': doc['id'], 'url': doc['url'],
                    'locator': chunk['locator'], 'excerpt': chunk['text']}
        answer = {'corpus_release': candidate['id'], 'model': settings.generation_model,
                  'status': 'answered' if substantive else 'insufficient_evidence',
                  'citations': [citation] if substantive else [],
                  'verified_claims': [{'text': 'Fixture only', 'citation_ids': [chunk['id']]}] if substantive else []}
        rows.append({'id': case['id'], 'question': case['question'], 'rubric': case['rubric'],
                     'as_of': case.get('as_of'), 'gold_chunk_ids': case.get('gold_chunk_ids', []),
                     'answer': answer, 'status': answer['status'], 'review': 'pass',
                     'review_note': 'Synthetic test only', 'review_method': 'Fixture validation',
                     'answer_sha256': hashlib.sha256(json.dumps(answer, ensure_ascii=False, sort_keys=True).encode()).hexdigest()})
    return {'storage_backend': 'postgresql', 'identity': {'release': candidate['id'],
            'configuration_sha256': configuration_fingerprint(settings)},
            'suite_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'results': rows}


@pytest.mark.parametrize('defect', ['sqlite', 'missing_case', 'changed_answer', 'changed_source', 'four_passes'])
def test_readiness_rejects_unbound_or_insufficient_model_evidence(store, settings, defect):
    from conftest import release
    candidate = release(store)
    settings = settings.model_copy(update={'database_url': SecretStr('postgresql://isolated')})
    report = natural_report(candidate, settings)
    assert model_gate(report, candidate, 'natural', settings)
    if defect == 'sqlite': report['storage_backend'] = 'sqlite'
    if defect == 'missing_case': report['results'].pop()
    if defect == 'changed_answer': report['results'][0]['answer']['status'] = 'limited'
    if defect == 'changed_source': candidate['documents'][0]['chunks'][0]['text'] = 'Different text'
    if defect == 'four_passes':
        for row in report['results'][:2]: row['review'] = 'partial'
    assert not model_gate(report, candidate, 'natural', settings)


def test_recorded_ready_boolean_cannot_override_recomputed_failure(tmp_path, monkeypatch):
    path = tmp_path/'approval.json'
    path.write_text(json.dumps({'ready': True, 'checked_at': utcnow().isoformat(), 'manifest': {}}))
    monkeypatch.setattr('scripts.check_release_readiness.inspect', lambda _: {'ready': False, 'blocked': ['source_freshness']})
    with pytest.raises(ValueError, match='source_freshness'):
        require_ready(path)


def test_candidate_evaluation_refuses_configuration_changes_in_same_output(tmp_path,settings,monkeypatch):
    from scripts.evaluate_generation_candidate import lock_configuration
    first=lock_configuration(settings,tmp_path)
    assert lock_configuration(settings,tmp_path)==first
    monkeypatch.setattr('scripts.evaluate_generation_candidate.configuration_fingerprint',lambda _: 'changed')
    with pytest.raises(ValueError,match='changed'):
        lock_configuration(settings,tmp_path)


def test_legacy_evaluation_checkpoint_cannot_be_resumed_under_different_source(tmp_path,settings):
    from scripts.evaluate_generation_candidate import lock_configuration
    metadata=tmp_path/'runs'/'historical'/'metadata.json'
    metadata.parent.mkdir(parents=True)
    metadata.write_text(json.dumps({'configuration_sha256':'different'}))
    with pytest.raises(ValueError,match='different'):
        lock_configuration(settings,tmp_path)
