import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from conftest import release
from landlaw.api import create_app
from test_agent import FakeProvider


def test_published_evaluation_archive_preserves_sources_failures_and_incomplete_runs():
    root = Path(__file__).resolve().parents[1]
    archive = json.loads((root/'reports/public-evaluations.json').read_text())
    for source in archive['sources']:
        assert hashlib.sha256((root/source['path']).read_bytes()).hexdigest() == source['sha256']
    current = next(r for r in archive['runs'] if r['configuration_sha256'].startswith('8db2d701'))
    assert [s['counts']['fail'] for s in current['suites']] == [2, 2, 3]
    natural = next(s for s in current['suites'] if s['split'] == 'natural')
    assert sum(row['review'] == 'pass' for row in natural['cases'] if row['id'] in {'N01','N02','N03','N04','N05','N06'}) == 2
    probe = next(r for r in archive['runs'] if r['configuration_sha256'].startswith('380801c7'))
    assert not probe['complete'] and probe['suites'][0]['counts']['not_run'] == 7
    assert len(archive['retrieval_runs']) == 35 and len(archive['faithfulness_runs']) == 2
    # Runtime receives only public benchmark summaries, not saved answers or trace payloads.
    for run in archive['runs']:
        for suite in run['suites']:
            for row in suite['cases']:
                assert not {'answer', 'trace', 'history', 'content', 'result'} & row.keys()


def test_api_keeps_partial_and_previous_runs_visible_and_never_relabels_their_identity(settings, store):
    release(store)
    settings.reports_dir.mkdir()
    runs = [
        {'id':'probe','release':'r1','configuration_sha256':'old-probe','complete':False,'suites':[]},
        {'id':'full','release':'r1','configuration_sha256':'old-full','complete':True,'suites':[]},
        {'id':'historical','release':'retired','configuration_sha256':'old-history','complete':True,'suites':[]},
    ]
    (settings.reports_dir/'public-evaluations.json').write_text(json.dumps({'runs':runs}))
    with TestClient(create_app(settings, store, FakeProvider(settings))) as client:
        response = client.get('/api/v1/evaluations/latest').json()
    assert response['default_run_id'] == 'full'
    assert len(response['runs']) == 3
    assert response['runs'][0]['configuration_sha256'] == 'old-probe'
    assert response['runs'][0]['matches_active_release']
    assert not response['runs'][0]['matches_active_configuration']
    assert not response['runs'][2]['matches_active_release']
