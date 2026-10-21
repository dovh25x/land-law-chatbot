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


@pytest.mark.parametrize('changed_path', ['backend/runtime.py', 'data/sources.json'])
def test_report_commit_does_not_invalidate_tested_revision_but_source_edits_do(tmp_path,monkeypatch,changed_path):
    import subprocess

    from scripts.check_release_readiness import revision_matches
    monkeypatch.chdir(tmp_path)
    def git(*args):
        return subprocess.check_output(['git',*args],text=True).strip()
    git('init','-q')
    for name in ['backend/runtime.py','data/sources.json']:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('original')
    git('add','.')
    git('-c','user.name=QA','-c','user.email=qa@example.invalid','commit','-qm','tested source')
    tested=git('rev-parse','HEAD')
    report=tmp_path/'reports/result.json';report.parent.mkdir();report.write_text('{}')
    git('add','.')
    git('-c','user.name=QA','-c','user.email=qa@example.invalid','commit','-qm','evidence only')
    head=git('rev-parse','HEAD')
    assert tested!=head and revision_matches(tested,head)
    (tmp_path/changed_path).write_text('untested change')
    assert not revision_matches(tested,head)


async def test_offline_guards_cannot_call_provider_or_clear_inherited_cooldown(tmp_path,settings,monkeypatch):
    from contextlib import contextmanager
    from datetime import timedelta
    from types import SimpleNamespace

    from landlaw.provider import ProviderUnavailable

    from scripts import evaluate_generation_candidate as helper
    output=tmp_path/'output';output.mkdir()
    cooldown=output/'operator-cooldown.json'
    original=json.dumps({'not_before':(utcnow()+timedelta(hours=1)).isoformat()})
    cooldown.write_text(original)
    @contextmanager
    def chosen_settings(*_):yield settings.model_copy(update={'reports_dir':output})
    monkeypatch.setattr(helper,'candidate_settings',chosen_settings)
    monkeypatch.setattr(helper,'frozen_dataset',lambda *_: ([{'id':'SAFE'}],'fixture-freeze'))
    monkeypatch.setattr(helper,'lock_source_policy',lambda *_: {'source_gate_sha256':None,'receipt_files_sha256':{}})
    class Store:
        def __init__(self,*_):pass
        def restore(self,*_):pass
        def close(self):pass
    class Provider:
        def __init__(self,*_,**__):pass
        async def generate(self,*_,**__):raise AssertionError('Network provider must not run')
        async def close(self):pass
    async def evaluate(_,store,provider,split,**kwargs):
        assert kwargs['case_ids']==['SAFE']
        with pytest.raises(ProviderUnavailable,match='disabled'):
            await provider.generate()
        metadata=output/'runs/fixture/metadata.json'
        metadata.parent.mkdir(parents=True)
        metadata.write_text('{}')
        return {'run_id':'fixture','results':[]}
    monkeypatch.setattr(helper,'Store',Store);monkeypatch.setattr(helper,'GroqProvider',Provider)
    monkeypatch.setattr(helper,'evaluate',evaluate)
    await helper.main(SimpleNamespace(output=output,resume=True,backup=tmp_path/'unused',
        postgres=False,split=['smoke'],case_id=['SAFE'],no_generation=True,source_receipt=[],source_gate=None))
    assert cooldown.read_text()==original
