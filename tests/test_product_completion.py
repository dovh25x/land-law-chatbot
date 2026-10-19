import json
from datetime import timedelta

from fastapi.testclient import TestClient

from conftest import release
from landlaw.api import create_app
from landlaw.catalog import references
from landlaw.ops import status
from landlaw.security import utcnow
from test_agent import FakeProvider


def test_reference_catalogue_exposes_only_public_provenance_not_local_paths(settings, store):
    release(store)
    settings.data_dir.mkdir()
    source={'id':'pending-law','title':'Văn bản gốc','source_kind':'legal','project':None,
        'url':'https://hanoi.gov.vn/van-ban','document_number':'1/2024/QĐ-UBND',
        'checked_at':utcnow().isoformat(),'review_status':'pending',
        'attachment_urls':['https://datafiles.chinhphu.vn/law.pdf','https://evil.example/fake.pdf'],
        'raw_paths':['/private/source.pdf'],'notes':'Internal processing notes'}
    outside={**source,'id':'outside','project':'olympic'}
    private={**source,'id':'private','contains_personal_data':True}
    (settings.data_dir/'sources.json').write_text(json.dumps([source,outside,private]))
    with TestClient(create_app(settings,store,FakeProvider(settings))) as client:
        result=client.get('/api/v1/documents').json()
        assert len(result['documents'])==1 and len(result['references'])==1
        ref=result['references'][0]
        assert ref['availability']=='reference_only' and not ref['applicability_verified']
        assert ref['attachment_urls']==['https://datafiles.chinhphu.vn/law.pdf']
        assert 'raw_paths' not in ref and 'notes' not in ref
        assert client.get('/api/v1/documents/pending-law').json()['document']==ref
        assert client.get('/api/v1/documents/outside').status_code==404
    assert references(settings,{'pending-law'})==[]


def test_intentional_snapshot_operation_warns_without_failing_health(settings, store):
    payload=release(store);payload['id']='old'
    payload['checked_at']=(utcnow()-timedelta(days=9)).isoformat()
    store.stage(payload);store.publish('old')
    assert status(store)['needs_attention']
    settings.allow_stale_generation=True
    report=status(store)
    assert not report['needs_attention'] and not report['sources_fresh']
    assert report['warnings']==['source_stale']


def test_default_deploy_preflight_does_not_require_model_review(monkeypatch):
    from scripts import deploy
    monkeypatch.setattr(deploy,'resolve_source_commit',lambda _: 'a'*40)
    monkeypatch.delenv('REQUIRE_QUALITY_READINESS',raising=False)
    monkeypatch.delenv('RELEASE_READINESS_REPORT',raising=False)
    assert deploy.preflight()=='a'*40


def test_importing_deploy_does_not_change_runtime_settings(tmp_path, monkeypatch):
    import importlib
    import os
    from scripts import deploy
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('ALLOW_STALE_GENERATION',raising=False)
    (tmp_path/'.env').write_text('ALLOW_STALE_GENERATION=true\n')
    importlib.reload(deploy)
    assert 'ALLOW_STALE_GENERATION' not in os.environ
