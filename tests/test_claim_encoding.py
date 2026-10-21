"""Source policy also constrains generation; verification remains mandatory."""
import json
from pathlib import Path

import pytest


def test_actual_unsourced_filing_draft_is_not_encodable_under_rule_only_policy():
    from landlaw.models import Draft
    from landlaw.provider import strict_generation_schema, validate_claim_policy
    policy={'kind':['legal_rule','applicability','context'],'section':['direct','explanation']}
    shape=strict_generation_schema(Draft,policy)
    fields=shape['$defs']['Claim']['properties']
    assert 'procedure' not in fields['kind']['enum'] and 'actions' not in fields['section']['enum']
    actual=Draft.model_validate(json.loads(Path('tests/fixtures/citizen-n01-unsolicited-action.json').read_text())['output'])
    with pytest.raises(ValueError,match='claim policy'):
        validate_claim_policy(actual,policy)
    direct=actual.model_copy(update={'claims':actual.claims[:1]})
    assert validate_claim_policy(direct,policy) is direct
    assert validate_claim_policy(actual,None) is actual


def test_encoding_policy_can_only_narrow_known_claim_enums():
    from landlaw.models import Draft
    from landlaw.provider import strict_generation_schema
    with pytest.raises(ValueError,match='claim policy'):
        strict_generation_schema(Draft,{'kind':['invented_kind']})
    allowed=strict_generation_schema(Draft,{'kind':['procedure','contact'],'section':['actions']})
    assert allowed['$defs']['Claim']['properties']['kind']['enum']==['procedure','contact']


@pytest.mark.parametrize('kind,status,days,expected',[
    ('legal','pending',0,[]),('legal','unchanged',1,['procedure']),
    ('official_directory','unchanged',1,['contact']),
    ('official_directory','unchanged',8,[]),('legal','changed',1,[])])
async def test_generation_roles_follow_the_actual_source_review(store,settings,kind,status,days,expected):
    from datetime import timedelta
    from conftest import document,release
    from test_agent import FakeProvider
    from landlaw.agent import Agent
    from landlaw.models import Evidence
    from landlaw.security import utcnow
    from landlaw.security import local_date
    doc=document().model_copy(update={'source_kind':kind,'operational_review_status':status,
        'operational_reviewed_at':utcnow()-timedelta(days=days)})
    payload=release(store,[doc])
    policy=await Agent(store,FakeProvider(settings)).synthesis_claim_policy({
        'release':payload,'as_of':local_date(),'evidence':[Evidence(document=doc,chunk=doc.chunks[0])]})
    assert policy['kind']==['legal_rule','applicability','context']+expected
    assert ('actions' in policy['section']) is bool(expected)
