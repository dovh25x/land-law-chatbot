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


@pytest.mark.parametrize('status', ['clarification_needed', 'limited'])
def test_export_does_not_transfer_an_old_review_to_a_new_answer(tmp_path, monkeypatch, status):
    monkeypatch.chdir(tmp_path)
    run = tmp_path / 'run';run.mkdir()
    output = tmp_path / 'output';output.mkdir()
    source = tmp_path / 'data/evaluation';source.mkdir(parents=True)
    (source / 'smoke.jsonl').write_text(json.dumps({'id':'S1','question':'Demo','rubric':['Check'],'gold_chunk_ids':[]})+'\n')
    answer = {'status':status,'corpus_release':'r1','model':'demo-model',
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
    assert report['results'][0]['citations_valid'] is None
    assert report['legal_acceptance'] is False
    checksum = hashlib.sha256(json.dumps(answer, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    assert report['results'][0]['answer_sha256']==checksum
    if status == 'limited':
        (output / 'reviews.json').write_text(json.dumps({'S1': {'answer_sha256':checksum,'verdict':'fail','note':'Provider quota prevented completion.'}}))
        module.export(run, output, release)
        reviewed = json.loads((output / 'evaluation.json').read_text())
        assert reviewed['status'] == 'reviewed'
        assert reviewed['execution_successful'] is False
        assert reviewed['metrics']['groups']['execution_failure']['fail'] == 1


def test_metrics_separate_behaviors_generation_and_missing_citation_telemetry():
    from landlaw.evaluation import report_metrics
    rows = [
        {'status': 'answered', 'review': 'fail', 'answer_origin': 'llm', 'gold_chunk_ids': ['gold'],
         'answer': {'elapsed_ms': 1000, 'llm_calls': 2, 'token_usage': 200, 'tool_calls': 3,
                    'retrieved_chunk_ids': ['gold']}},
        {'status': 'insufficient_evidence', 'review': 'pass', 'answer_origin': 'deterministic',
         'answer': {'elapsed_ms': 10, 'llm_calls': 0, 'token_usage': 0, 'tool_calls': 0}},
        {'status': 'clarification_needed', 'review': 'pass', 'gold_chunk_ids': ['missing'],
         'answer': {'elapsed_ms': 20}},
    ]
    metrics = report_metrics(rows)
    assert metrics['groups']['answered'] == {'cases': 1, 'pass': 0, 'partial': 0, 'fail': 1, 'awaiting_review': 0}
    assert metrics['groups']['insufficient']['pass'] == 1
    assert metrics['answer_origin'] == {'llm': 1, 'deterministic': 1, 'unknown': 1}
    assert metrics['usage']['llm_calls']['samples'] == 2
    assert metrics['usage']['elapsed_ms']['median'] == 20
    assert metrics['usage']['elapsed_ms']['p95'] == 1000
    assert metrics['evidence_hit_at_8']['eligible_cases'] == 2
    assert metrics['evidence_hit_at_8']['measured_cases'] == 1
    assert metrics['evidence_hit_at_8']['rate'] == 1


def test_secret_patterns_work_without_a_local_env_and_do_not_report_values(tmp_path):
    spec = importlib.util.spec_from_file_location('secret_scanner', Path('scripts/check_secrets.py'))
    scanner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanner)
    path = tmp_path / 'leak.ts'
    secret = 'gsk_' + 'a' * 40
    path.write_text('const value = ' + repr(secret))
    assert scanner.find_leaks([path]) == [str(path)]
    path.write_text('const value = "GROQ_API_KEY"')
    assert scanner.find_leaks([path]) == []
