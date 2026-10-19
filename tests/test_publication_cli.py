from datetime import timedelta
from types import SimpleNamespace

import pytest
import typer
from conftest import document
from landlaw import cli
from landlaw.embedding import contract
from landlaw.security import utcnow


@pytest.mark.parametrize('blocked_by', ['dependency', 'freshness'])
def test_publish_rejects_embedded_candidate_before_backup_or_activation(settings, store, monkeypatch, blocked_by):
    ids = ['luat-dat-dai-2024', 'nd-88-2024', 'nd-226-2025', 'qd-56-2024-hanoi',
           'qd-40-2026-hanoi', 'nq-52-2025-hanoi']
    docs = [document(ident) for ident in ids]
    docs.append(document('project', project='ring4').model_copy(update={'source_kind': 'project_decision'}))
    stamp = utcnow() - timedelta(days=10 if blocked_by == 'freshness' else 0)
    payload = {'id': 'candidate', 'checked_at': stamp.isoformat(), 'embedded': True,
               'documents': [doc.model_dump(mode='json') for doc in docs],
               'embedding_contract': contract(settings), 'embedding_dimensions': 384}
    for doc in payload['documents']:
        doc['checked_at'] = stamp.isoformat()
        for chunk in doc['chunks']:
            chunk['embedding'] = [1.0] + [0.0]*383
    if blocked_by == 'dependency':
        payload['unresolved_relations'] = [{'source_id': 'project', 'target_id': 'missing'}]

    def forbidden(*_):
        pytest.fail('Rejected candidate must not trigger backup or activation')

    selected = SimpleNamespace(release=lambda _: payload, source_fresh=store.source_fresh,
                               backup=forbidden, publish=forbidden, close=lambda: None)
    monkeypatch.setattr(cli, 'Settings', lambda: settings)
    monkeypatch.setattr(cli, 'Store', lambda _: selected)
    with pytest.raises(typer.BadParameter, match='publication blocked'):
        cli.publish('candidate', require_quality=True)
    assert store.state('active_release') is None


def test_publish_without_quality_gate_preserves_actual_freshness(settings, store, monkeypatch):
    doc=document().model_dump(mode='json')
    stamp=(utcnow()-timedelta(days=10)).isoformat()
    doc['checked_at']=stamp
    payload={'id':'candidate','checked_at':stamp,'documents':[doc]}
    store.stage(payload)
    monkeypatch.setattr(cli,'Settings',lambda:settings)
    monkeypatch.setattr(cli,'Store',lambda _:store)
    monkeypatch.setattr(store,'close',lambda:None)
    cli.publish('candidate')
    assert store.state('active_release')=='candidate'
    assert not store.source_fresh(store.release())
