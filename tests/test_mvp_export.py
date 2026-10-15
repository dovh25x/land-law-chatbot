import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

spec = importlib.util.spec_from_file_location('mvp_export', Path('scripts/export_mvp_evaluation.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_export_rejects_a_different_configuration_before_writing_report(tmp_path, monkeypatch):
    run = tmp_path / 'run';run.mkdir()
    (run / 'records.json').write_text('[]')
    (run / 'metadata.json').write_text('{"configuration_sha256":"old-config"}')
    monkeypatch.setattr(module, 'Settings', lambda: None)
    monkeypatch.setattr(module, 'configuration_fingerprint', lambda _: 'new-config')
    output = tmp_path / 'output'
    with pytest.raises(ValueError, match='Configuration mismatch'):
        module.export(run, output, tmp_path / 'release.json')
    assert not output.exists()


def test_export_does_not_transfer_an_old_review_to_a_new_answer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run = tmp_path / 'run';run.mkdir()
    output = tmp_path / 'output';output.mkdir()
    source = tmp_path / 'data/evaluation';source.mkdir(parents=True)
    (source / 'smoke.jsonl').write_text(json.dumps({'id':'S1','question':'Demo','rubric':['Check'],'gold_chunk_ids':[]})+'\n')
    answer = {'status':'clarification_needed','corpus_release':'r1','model':'demo-model',
              'elapsed_ms':10,'content':'Need facts','citations':[]}
    (run / 'records.json').write_text(json.dumps([{'case_id':'S1','mode':'agentic','result':answer}]))
    (run / 'metadata.json').write_text('{"configuration_sha256":"config"}')
    (output / 'reviews.json').write_text('{"S1":{"answer_sha256":"old-answer","verdict":"pass","note":"Old"}}')
    release = tmp_path / 'release.json';release.write_text('{"id":"r1","documents":[]}')
    monkeypatch.setattr(module, 'Settings', lambda: SimpleNamespace(generation_model='demo-model'))
    monkeypatch.setattr(module, 'configuration_fingerprint', lambda _: 'config')
    module.export(run, output, release)
    report = json.loads((output / 'evaluation.json').read_text())
    assert report['status']=='awaiting_review'
    assert report['results'][0]['review']=='awaiting_review'
    assert report['legal_acceptance'] is False
    checksum = hashlib.sha256(json.dumps(answer, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert report['results'][0]['answer_sha256']==checksum
