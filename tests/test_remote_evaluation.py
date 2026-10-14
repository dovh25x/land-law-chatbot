import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('remote_evaluation',Path(__file__).parents[1]/'scripts/run_remote_evaluation.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@pytest.fixture(autouse=True)
def isolated_runner_environment(monkeypatch):
    for key in ('EVALUATION_RELEASE','EVALUATION_SPLIT','EVALUATION_LIMIT','EVALUATION_CONCURRENCY','EVALUATION_CASE_IDS'):
        monkeypatch.delenv(key,raising=False)


def test_remote_evaluation_keeps_selected_suite_release_and_bounded_concurrency(monkeypatch):
    monkeypatch.setenv('EVALUATION_RELEASE','corpus-de584c31fc95f9a2');monkeypatch.setenv('EVALUATION_SPLIT','acceptance')
    monkeypatch.setenv('EVALUATION_LIMIT','160');monkeypatch.setenv('EVALUATION_CONCURRENCY','2')
    calls=[];monkeypatch.setattr(module.subprocess,'run',lambda args,check: calls.append(args))
    module.main()
    assert calls==[['land-law','benchmark','--release-id','corpus-de584c31fc95f9a2','--split','acceptance','--limit','160','--concurrency','2']]


@pytest.mark.parametrize('key,value',[('EVALUATION_CONCURRENCY','8'),('EVALUATION_LIMIT','241'),('EVALUATION_SPLIT','accepted'),('EVALUATION_RELEASE','corpus-x; shell')])
def test_invalid_remote_evaluation_never_starts_subprocess(monkeypatch,key,value):
    monkeypatch.setenv('EVALUATION_RELEASE','corpus-de584c31fc95f9a2');monkeypatch.setenv('EVALUATION_SPLIT','smoke')
    monkeypatch.setenv('EVALUATION_LIMIT','40');monkeypatch.setenv('EVALUATION_CONCURRENCY','2');monkeypatch.setenv(key,value)
    def forbidden(*args,**kwargs):raise AssertionError('Invalid configuration reached execution')
    monkeypatch.setattr(module.subprocess,'run',forbidden)
    with pytest.raises(SystemExit):module.main()


def test_priority_cases_do_not_change_suite_or_run_configuration(monkeypatch):
    monkeypatch.setenv('EVALUATION_RELEASE','corpus-de584c31fc95f9a2');monkeypatch.setenv('EVALUATION_SPLIT','smoke')
    monkeypatch.setenv('EVALUATION_LIMIT','40');monkeypatch.setenv('EVALUATION_CONCURRENCY','2');monkeypatch.setenv('EVALUATION_CASE_IDS','S12,S15')
    calls=[];monkeypatch.setattr(module.subprocess,'run',lambda args,check: calls.append(args))
    module.main()
    assert calls[0][-2:]==['--case-ids','S12,S15'] and calls[0][4]=='--split' and calls[0][5]=='smoke'
