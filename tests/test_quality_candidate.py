from conftest import supplied_synthesis_fixture
import json
from datetime import date
from pathlib import Path
import pytest
from conftest import document,release
from test_agent import FakeProvider,noop
from landlaw.agent import Agent,Plan,Verification
from landlaw.models import ChatRequest,Claim,Draft,Evidence
from landlaw.provider import Budget

@pytest.mark.parametrize('question,include_adjacent',[
 ('Chưa được bố trí chỗ ở mới thì việc thu hồi đất ở và tái định cư cần bảo đảm gì?',False),
 ('Theo Điều 91 và Điều 111, chưa bố trí chỗ ở mới thì cần bảo đảm gì?',True),
 ('Nguyên tắc bồi thường, hỗ trợ và tái định cư là gì?',True)])
def test_prerequisite_focus_keeps_whole_article_and_external_evidence(store,settings,question,include_adjacent):
 fixture=json.loads(Path('tests/fixtures/citizen-n04-negative-premise.json').read_text());doc=document().model_copy(update={'id':fixture['sources'][0]['document_id'],'chunks':[]})
 for item in fixture['sources']:
  doc.chunks.append(document().chunks[0].model_copy(update={'id':item['id'],'document_id':doc.id,'text':item['excerpt'],'locator':item['locator']}))
 amendment=document('amendment',text='Điều1. Sửa đổi điều kiện về thời điểm áp dụng quy định. Fixture, không làm căn cứ pháp luật.')
 state={'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000',message=question),
  'evidence':[Evidence(document=doc,chunk=c,applicability='current') for c in doc.chunks]+[Evidence(document=amendment,chunk=amendment.chunks[0],applicability='current')],
  'release':{'documents':[doc.model_dump(mode='json'),amendment.model_dump(mode='json')],'relations':[]}}
 passages,_=Agent(store,FakeProvider(settings)).prompt_context(state);ids={p['citation_id'] for p in passages}
 assert ('luat-dat-dai-2024-109-1-0' in ids) is include_adjacent
 assert {s['id'] for s in fixture['sources'] if s['locator'].startswith('Điều91') or s['locator'].startswith('Điều 91')}<=ids
 assert amendment.chunks[0].id in ids

@pytest.mark.parametrize('qualified',[False,True])
async def test_damage_compensation_retains_the_source_causal_event(store,settings,qualified):
 fixture=json.loads(Path('tests/fixtures/citizen-n01-damage-scope.json').read_text());source=fixture['sources'][0];doc=document(text=source['excerpt']).model_copy(update={'id':source['document_id']});doc.chunks[0].id=source['id'];doc.chunks[0].document_id=doc.id;doc.chunks[0].locator=source['locator'];payload=release(store,[doc])
 text=fixture['claims'][0]['text'] if not qualified else 'Khi Nhà nước thu hồi đất mà phải di chuyển tài sản, được bồi thường chi phí tháo dỡ, di chuyển, lắp đặt; với hệ thống máy móc, dây chuyền sản xuất còn được bồi thường thiệt hại phát sinh trong quá trình tháo dỡ, vận chuyển, lắp đặt.'
 state={'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000',message='Máy móc tháo ra bị hư hại khi phải di dời do thu hồi đất, có khoản bồi thường nào?'),
 'budget':Budget(),'release':payload,'as_of':date(2024,8,2),'plan':Plan(),'evidence':[Evidence(document=doc,chunk=doc.chunks[0],applicability='current')],
 'draft':Draft(status='answered',claims=[Claim(text=text,citation_ids=[doc.chunks[0].id])]),'trace':[],'emit':noop}
 agent=Agent(store,FakeProvider(settings,verification=Verification(supported_claim_indexes=[0])));supplied_synthesis_fixture(state);await agent.verify(state);await agent.finish(state)
 assert bool(state['result'].verified_claims) is qualified
