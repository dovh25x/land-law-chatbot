"""Citizen interaction and publication boundaries, independent of model approval."""
from datetime import timedelta

import pytest

from conftest import document
from landlaw.security import utcnow


def test_receiving_an_unknown_paper_asks_one_question_without_requesting_private_data():
    from landlaw.citizen import assess_need
    need = assess_need('Tôi vừa nhận giấy về Vành đai 4, cần bắt đầu từ đâu?', [])
    assert need.clarification.fact == 'document_type'
    assert len(need.clarification.options) == 2 and need.clarification.allow_unknown
    assert 'ảnh' not in need.clarification.question
    assert need.document_type is None


def test_user_corrections_override_old_paper_and_assistant_history_is_not_a_fact():
    from landlaw.citizen import assess_need
    history = [{'role':'user','content':'Tôi có thông báo thu hồi đất.'},
               {'role':'assistant','content':'Bạn đã có quyết định thu hồi đất.'}]
    need = assess_need('Tôi xem lại, là quyết định thu hồi đất, không phải thông báo.', history)
    assert need.document_type == 'recovery_decision'
    assert need.fact_origin == 'current_user'
    assert assess_need('Giấy đó là gì?', history).document_type == 'recovery_notice'
    assert assess_need('Tôi xem lại, không có thông báo thu hồi đất.', history).document_type is None
    assert assess_need('Không phải thông báo thu hồi đất, mà là quyết định thu hồi đất.', history).document_type == 'recovery_decision'
    assert assess_need('Tôi không rõ tên giấy.', history).document_type is None


def test_unknown_paper_has_a_way_out_and_a_definition_needs_no_case_file():
    from landlaw.citizen import assess_need
    history = [{'role':'user','content':'Tôi vừa nhận giấy về Vành đai 4.'},
               {'role':'assistant','content':'Trên giấy ghi tên nào?'}]
    need = assess_need('Tôi không rõ tên giấy.', history)
    assert need.clarification is None and need.orientation_only
    assert assess_need('Tôi muốn hiểu tái định cư nghĩa là gì?', []).general_question


def test_contact_and_procedure_roles_cannot_be_approved_from_news_or_old_directory():
    from landlaw.citizen import source_policy_issues
    from landlaw.models import Claim, Evidence
    news=document().model_copy(update={'source_kind':'official_news'})
    action=Claim(kind='contact',text='Nộp tại cơ quan này.',citation_ids=[news.chunks[0].id])
    assert source_policy_issues(action,[Evidence(document=news,chunk=news.chunks[0])],utcnow().date())
    directory=document().model_copy(update={'source_kind':'official_directory',
        'operational_reviewed_at':utcnow()-timedelta(days=8),'operational_review_status':'unchanged'})
    assert source_policy_issues(action,[Evidence(document=directory,chunk=directory.chunks[0])],utcnow().date())


def test_structured_sections_cannot_hide_an_orphan_or_repeat_a_claim():
    from landlaw.models import AnswerSection, ChatResult, Claim
    base=dict(status='answered',content='Nguồn.',as_of=utcnow().date(),trace_id='test',model='test',
              embedding_model='test',mode='agentic',answer_schema_version=2,
              verified_claims=[Claim(text='Một quy định.',citation_ids=['source'])])
    with pytest.raises(ValueError):
        ChatResult(**base,answer_sections=[AnswerSection(kind='direct',claim_indexes=[1])])
    with pytest.raises(ValueError):
        ChatResult(**base,answer_sections=[AnswerSection(kind='direct',claim_indexes=[0]),
                                          AnswerSection(kind='actions',claim_indexes=[0])])


def test_draft_suite_is_never_executable_and_custom_registry_requires_review(tmp_path):
    from pathlib import Path
    from landlaw.evaluation import frozen_dataset
    with pytest.raises(ValueError, match='draft|review|frozen'):
        frozen_dataset(Path('data'),'citizen-v2-draft')


def test_recent_directory_proves_public_contact_but_not_a_receiving_authority():
    from landlaw.citizen import source_policy_issues
    from landlaw.models import Claim, Evidence
    directory=document().model_copy(update={'source_kind':'official_directory',
        'operational_reviewed_at':utcnow(),'operational_review_status':'unchanged'})
    evidence=[Evidence(document=directory,chunk=directory.chunks[0])]
    contact=Claim(kind='contact',text='Số điện thoại công khai của cơ quan là số được ghi trong đoạn nguồn.',citation_ids=[directory.chunks[0].id])
    assert source_policy_issues(contact,evidence,utcnow().date())==[]
    assert source_policy_issues(contact.model_copy(update={'text':'Nộp hồ sơ tại cơ quan này.'}),evidence,utcnow().date())
    assert source_policy_issues(contact.model_copy(update={'kind':'legal_rule','text':'Hồ sơ gồm các giấy bắt buộc.'}),evidence,utcnow().date())
    assert source_policy_issues(contact.model_copy(update={'kind':'context','text':'Cơ quan này nhận hồ sơ.'}),evidence,utcnow().date())


def test_unknown_answers_do_not_produce_an_endless_clarification_loop():
    from landlaw.citizen import clarification_for_missing, repeated_clarification
    question=clarification_for_missing(['Ngày phê duyệt'])
    history=[{'role':'user','content':'Tôi muốn đối chiếu quy định cho giấy này.'},
             {'role':'assistant','content':question.question}]
    assert repeated_clarification(question,history,'Tôi không biết ngày.')
    assert not repeated_clarification(question,history,'Ngày tôi đọc được là 01/01/2024.')


async def test_paper_orientation_uses_no_model_and_never_turns_unknown_into_an_entitlement(store,settings):
    from conftest import release, session
    from test_agent import FakeProvider, noop
    from landlaw.agent import Agent
    from landlaw.models import ChatRequest
    release(store)
    sid,_=session(store)
    class NoModel(FakeProvider):
        async def generate(self,*args,**kwargs):
            raise AssertionError('A paper-identification question needs no model')
    result=await Agent(store,NoModel(settings)).run(ChatRequest(session_id=sid,
        message='Tôi vừa nhận giấy về Vành đai 4, cần bắt đầu từ đâu?'),noop)
    assert result.answer_schema_version==2 and result.status=='clarification_needed'
    assert result.clarification.fact=='document_type'
    assert result.llm_calls==result.tool_calls==0
    assert not result.verified_claims and not result.citations


def test_only_the_latest_explicit_operational_review_can_enable_an_action(store,settings,tmp_path):
    import json
    from conftest import release
    from landlaw.ops import record_source_review
    doc=document()
    release(store,[doc])
    receipt={'document_id':doc.id,'checksum':doc.checksum,'checked_at':utcnow().isoformat(),
             'status':'unchanged','relation_review':'Fixture review, not a real legal approval.',
             'evidence_urls':['https://hanoi.gov.vn/'],
             'operational_review':{'source_role_checked':True,'jurisdiction_checked':True,
                                   'procedure_and_dependencies_checked':True}}
    path=tmp_path/'receipt.json';path.write_text(json.dumps(receipt));record_source_review(store,path)
    assert store.operational_review(doc,'r1').operational_review_status=='unchanged'
    receipt.update(status='changed',checked_at=utcnow().isoformat())
    path.write_text(json.dumps(receipt));record_source_review(store,path)
    assert store.operational_review(doc,'r1').operational_review_status=='changed'


def test_custom_suite_cannot_escape_directory_or_claim_reviewed_gold_by_presence_only(tmp_path):
    import hashlib,json
    from landlaw.evaluation import frozen_dataset
    base=tmp_path/'evaluation';base.mkdir()
    case={'id':'V01','split':'citizen-v2','question':'Câu hỏi fixture','as_of':'2026-10-19',
          'review_status':'reviewed','answerability':'answerable','rubric':['Fixture tiêu chí'],
          'gold_chunk_ids':['source-1']}
    path=base/'v2.jsonl';path.write_text(json.dumps(case)+'\n')
    freeze={'suite_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'cases':1,'status':'frozen',
            'annotation_status':'reviewed','corpus_id':'fixture','review_method':'fixture','reviewed_by_role':'fixture'}
    (base/'v2.freeze.json').write_text(json.dumps(freeze))
    registry={'suites':{'citizen-v2':{'path':'v2.jsonl','freeze_path':'v2.freeze.json','cases':1,'executable':True}}}
    (base/'registry.json').write_text(json.dumps(registry))
    with pytest.raises(ValueError,match='reviewed legal'):
        frozen_dataset(tmp_path,'citizen-v2')
    case.update(answerability='interaction_only')
    path.write_text(json.dumps(case)+'\n');freeze['suite_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    (base/'v2.freeze.json').write_text(json.dumps(freeze))
    assert len(frozen_dataset(tmp_path,'citizen-v2')[0])==1
    registry['suites']['citizen-v2']['path']='../outside.jsonl'
    (base/'registry.json').write_text(json.dumps(registry))
    with pytest.raises(ValueError,match='outside'):
        frozen_dataset(tmp_path,'citizen-v2')


def test_task_metrics_keep_unrun_cases_and_cannot_reward_false_abstention():
    from landlaw.evaluation import citizen_metrics
    cases=[{'id':'a','answerability':'answerable'},{'id':'b','answerability':'answerable'},
           {'id':'c','answerability':'missing_source'}]
    rows=[{'id':'a','status':'insufficient_evidence','review':'pass'},
          {'id':'c','status':'insufficient_evidence','review':'pass'}]
    groups=citizen_metrics(rows,cases)['groups']
    assert groups['answerable']=={'expected':2,'counts':{'pass':0,'partial':0,'fail':1,'awaiting_review':0,'not_run':1},'false_abstention':1}
    assert groups['missing_source']['counts']['pass']==1


def test_complete_evidence_requires_every_group_and_every_chunk_of_an_alternative():
    from landlaw.evaluation import evidence_group_coverage, validate_evidence_annotation
    groups=[{'id':'authority','alternatives':[['a','b'],['equivalent']]},
            {'id':'contact','alternatives':[['c']]}]
    case={'gold_chunk_ids':['a','b','c'],'required_propositions':['Fixture proposition'],
          'required_evidence_groups':groups}
    validate_evidence_annotation(case)
    assert not evidence_group_coverage(['a','c'],groups)['complete']
    assert evidence_group_coverage(['a','b','c'],groups)['complete']
    assert evidence_group_coverage(['equivalent','c'],groups)['complete']
    with pytest.raises(ValueError,match='alternatives'):
        validate_evidence_annotation({**case,'required_evidence_groups':[{'id':'bad','alternatives':'a'}]})


async def test_expired_action_vetoes_the_entire_group_even_after_model_approval(store,settings):
    from conftest import release
    from test_agent import FakeProvider, noop
    from landlaw.agent import Agent, Plan, Verification
    from landlaw.models import ChatRequest, Claim, Draft, Evidence
    from landlaw.provider import Budget
    doc=document();payload=release(store,[doc])
    draft=Draft(status='answered',claims=[
        Claim(text='Thông tin có căn cứ.',citation_ids=[doc.chunks[0].id]),
        Claim(kind='procedure',section='actions',text='Nộp hồ sơ tại cơ quan này.',citation_ids=[doc.chunks[0].id])],
        next_steps=['Nộp ngay trong ngày mai.'])
    state={'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000',message='Hỏi thủ tục.'),
           'budget':Budget(),'release':payload,'as_of':utcnow().date(),'plan':Plan(),
           'evidence':[Evidence(document=doc,chunk=doc.chunks[0],applicability='current')],
           'draft':draft,'verification':Verification(supported_claim_indexes=[0,1]),'trace':[],'emit':noop}
    await Agent(store,FakeProvider(settings)).finish(state)
    result=state['result']
    assert result.status=='insufficient_evidence' and not result.verified_claims and not result.citations
    assert 'Nộp' not in result.content


@pytest.mark.parametrize('qualified',[False,True])
async def test_actual_n02_omissions_are_blocked_even_if_the_model_approves(store,settings,qualified):
    import json
    from datetime import date
    from pathlib import Path
    from conftest import release
    from test_agent import FakeProvider, noop
    from landlaw.agent import Agent, Plan, Verification
    from landlaw.models import ChatRequest, Claim, Draft, Evidence
    from landlaw.provider import Budget
    fixture=json.loads(Path('tests/fixtures/citizen-n02-qualification.json').read_text())
    doc=document(text=fixture['source'],document_number='88/2024/NĐ-CP')
    doc.chunks[0].locator='Điều 19 · ngữ cảnh'
    payload=release(store,[doc])
    text=('Hộ gia đình, cá nhân đang sử dụng đất nông nghiệp nếu đủ điều kiện được bồi thường về đất, '
          'bị thu hồi từ 30% đến 70% diện tích đang sử dụng, được hỗ trợ ổn định đời sống trong 6 tháng '
          'nếu không phải di chuyển chỗ ở; mức hỗ trợ cho một nhân khẩu tính bằng tiền tương đương '
          '30 kg gạo trong 01 tháng theo thời giá trung bình tại thời điểm hỗ trợ của địa phương.') if qualified else fixture['claim']
    draft=Draft(status='answered',claims=[Claim(text=text,citation_ids=[doc.chunks[0].id])])
    state={'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000',message='Hỗ trợ ổn định đời sống phụ thuộc những gì?'),
           'budget':Budget(),'release':payload,'as_of':date(2024,8,2),'plan':Plan(),
           'evidence':[Evidence(document=doc,chunk=doc.chunks[0],applicability='current')],
           'draft':draft,'trace':[],'emit':noop}
    agent=Agent(store,FakeProvider(settings,verification=Verification(supported_claim_indexes=[0])))
    await agent.verify(state)
    await agent.finish(state)
    assert bool(state['result'].verified_claims) is qualified
    if not qualified:
        assert not state['result'].citations and text not in state['result'].content


@pytest.mark.parametrize('variant',['actual','contract_paraphrase','exclusive_benefit'])
async def test_n02_contract_paraphrase_cannot_lose_source_actor_scope(store,settings,variant):
    import json
    from datetime import date
    from pathlib import Path
    from conftest import release
    from test_agent import FakeProvider, noop
    from landlaw.agent import Agent, Plan, Verification
    from landlaw.models import ChatRequest, Claim, Draft, Evidence
    from landlaw.provider import Budget
    fixture=json.loads(Path('tests/fixtures/citizen-n02-contract-scope.json').read_text())
    doc=document(text=fixture['source'],document_number='88/2024/NĐ-CP')
    doc.chunks[0].locator='Điều 19 · ngữ cảnh';payload=release(store,[doc])
    text={'actual':fixture['claim'],
          'contract_paraphrase':'Hộ sử dụng đất theo hợp đồng giao khoán được hỗ trợ ổn định đời sống do UBND cấp tỉnh quyết định mức hỗ trợ.',
          'exclusive_benefit':'Hỗ trợ ổn định đời sống chỉ áp dụng cho hộ đủ điều kiện được bồi thường về đất.'}[variant]
    draft=Draft(status='answered',claims=[Claim(text=text,citation_ids=[doc.chunks[0].id])])
    state={'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000',message='Hỗ trợ ổn định đời sống phụ thuộc những gì?'),
           'budget':Budget(),'release':payload,'as_of':date(2024,8,2),'plan':Plan(),
           'evidence':[Evidence(document=doc,chunk=doc.chunks[0],applicability='current')],
           'draft':draft,'trace':[],'emit':noop}
    agent=Agent(store,FakeProvider(settings,verification=Verification(supported_claim_indexes=[0])))
    await agent.verify(state);await agent.finish(state)
    assert not state['result'].verified_claims and not state['result'].citations


@pytest.mark.parametrize('reference,expected', [('khoản 1 Điều 104',False),('khoản 2 Điều 104',True),('Điều 104',True),('cost_scope',True)])
async def test_actual_n05_authority_cannot_be_attributed_to_the_cost_clause(store,settings,reference,expected):
    import json
    from datetime import date
    from pathlib import Path
    from conftest import release
    from test_agent import FakeProvider, noop
    from landlaw.agent import Agent, Plan, Verification
    from landlaw.models import ChatRequest, Claim, Draft, Evidence
    from landlaw.provider import Budget
    fixture=json.loads(Path('tests/fixtures/citizen-n05-authority-clause.json').read_text())
    doc=document(text=fixture['source']);doc.chunks[0].locator='Điều 104'
    payload=release(store,[doc])
    text=fixture['claim'].replace('khoản 1 Điều 104',reference)
    if reference=='cost_scope':
        text='Ủy ban nhân dân cấp tỉnh quy định mức bồi thường tại khoản 1 Điều 104.'
    state={'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000',message='Ai quy định mức bồi thường chi phí di chuyển tài sản?'),
           'budget':Budget(),'release':payload,'as_of':date(2024,8,2),'plan':Plan(),
           'evidence':[Evidence(document=doc,chunk=doc.chunks[0],applicability='current')],
           'draft':Draft(status='answered',claims=[Claim(text=text,citation_ids=[doc.chunks[0].id])]),
           'trace':[],'emit':noop}
    agent=Agent(store,FakeProvider(settings,verification=Verification(supported_claim_indexes=[0])))
    await agent.verify(state);await agent.finish(state)
    assert bool(state['result'].verified_claims) is expected
    if not expected:
        assert not state['result'].citations and text not in state['result'].content


@pytest.mark.parametrize('case,qualified', [('N03',False),('N03',True),('X02',False),('X02',True)])
async def test_actual_support_claims_cannot_broaden_agricultural_beneficiaries(store,settings,case,qualified):
    import json
    from datetime import date
    from pathlib import Path
    from conftest import release
    from test_agent import FakeProvider, noop
    from landlaw.agent import Agent, Plan, Verification
    from landlaw.models import ChatRequest, Claim, Draft, Evidence
    from landlaw.provider import Budget
    fixture=next(row for row in json.loads(Path('tests/fixtures/citizen-agricultural-actor-loss.json').read_text()) if row['id']==case)
    docs={}
    evidence=[]
    for source in fixture['sources']:
        doc=docs.setdefault(source['document_id'],document().model_copy(update={'id':source['document_id'],'chunks':[]}))
        chunk=document().chunks[0].model_copy(update={'id':source['id'],'document_id':doc.id,'text':source['excerpt'],'locator':source['locator']})
        doc.chunks.append(chunk);evidence.append(Evidence(document=doc,chunk=chunk,applicability='current'))
    payload=release(store,list(docs.values()))
    claims=[Claim.model_validate(c) for c in fixture['claims']]
    if qualified:
        claims=[Claim(text='Hộ gia đình, cá nhân trực tiếp sản xuất nông nghiệp đang sử dụng đất nông nghiệp do được Nhà nước giao, khi Nhà nước thu hồi đất không có đất để bồi thường và đã được bồi thường bằng tiền, thuộc nhóm được hỗ trợ tại điểm a khoản 1 và khoản 2 Điều 109: hỗ trợ bằng hình thức đào tạo, chuyển đổi nghề và tìm kiếm việc làm.',
            citation_ids=[e.chunk.id for e in evidence if e.chunk.locator.startswith('Điều 109')])]
    state={'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000',message='Người trực tiếp làm nông bị thu hồi đất có được hỗ trợ chuyển nghề không?'),
           'budget':Budget(),'release':payload,'as_of':date(2024,8,2),'plan':Plan(),'evidence':evidence,
           'draft':Draft(status='answered',claims=claims),'trace':[],'emit':noop}
    agent=Agent(store,FakeProvider(settings,verification=Verification(supported_claim_indexes=list(range(len(claims))))))
    await agent.verify(state);await agent.finish(state)
    assert bool(state['result'].verified_claims) is qualified


@pytest.mark.parametrize('use_source_rule',[False,True])
async def test_unmet_user_housing_premise_is_not_a_new_statutory_trigger(store,settings,use_source_rule):
    import json
    from datetime import date
    from pathlib import Path
    from conftest import release
    from test_agent import FakeProvider, noop
    from landlaw.agent import Agent, Plan, Verification
    from landlaw.models import ChatRequest, Claim, Draft, Evidence
    from landlaw.provider import Budget
    fixture=json.loads(Path('tests/fixtures/citizen-n04-negative-premise.json').read_text())
    docs=[]
    for source in fixture['sources']:
        doc=document(text=source['excerpt']).model_copy(update={'id':source['document_id']})
        doc.chunks[0].id=source['id'];doc.chunks[0].document_id=doc.id;doc.chunks[0].locator=source['locator']
        docs.append(doc)
    # All passages are from the same act; retain them in one fixture document.
    doc=docs[0].model_copy(update={'chunks':[d.chunks[0] for d in docs]})
    payload=release(store,[doc])
    text=('Việc phê duyệt phương án bồi thường, hỗ trợ, tái định cư và việc bố trí tái định cư '
          'phải được hoàn thành trước khi có quyết định thu hồi đất.') if use_source_rule else fixture['claim']
    state={'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000',message='Chưa được bố trí chỗ ở mới thì thu hồi đất cần bảo đảm gì?'),
           'budget':Budget(),'release':payload,'as_of':date(2024,8,2),'plan':Plan(),
           'evidence':[Evidence(document=doc,chunk=c,applicability='current') for c in doc.chunks],
           'draft':Draft(status='answered',claims=[Claim(text=text,citation_ids=[c.id for c in doc.chunks])]),
           'trace':[],'emit':noop}
    agent=Agent(store,FakeProvider(settings,verification=Verification(supported_claim_indexes=[0])))
    await agent.verify(state);await agent.finish(state)
    assert bool(state['result'].verified_claims) is use_source_rule
    if not use_source_rule:
        assert not state['result'].citations


@pytest.mark.parametrize('variant,expected',[('actual',False),('actor_as_condition',False),('qualified_alternatives',True)])
async def test_s06_actor_classes_cannot_be_alternative_qualifying_documents(store,settings,variant,expected):
    import json
    from datetime import date
    from pathlib import Path
    from conftest import release
    from test_agent import FakeProvider, noop
    from landlaw.agent import Agent, Plan, Verification
    from landlaw.models import ChatRequest, Claim, Draft, Evidence
    from landlaw.provider import Budget
    fixture=json.loads(Path('tests/fixtures/citizen-s06-actor-condition.json').read_text())
    doc=document().model_copy(update={'id':fixture['sources'][0]['document_id']})
    doc.chunks=[doc.chunks[0].model_copy(update={'id':s['id'],'document_id':doc.id,'text':s['excerpt'],'locator':s['locator']}) for s in fixture['sources']]
    payload=release(store,[doc])
    text={
      'actual':fixture['claim'],
      'actor_as_condition':'Phải thuộc đối tượng tại khoản 1 Điều 95. Giấy chứng nhận không phải điều kiện duy nhất vì còn có các điều kiện khác như: có quyết định giao đất; thuộc trường hợp cộng đồng dân cư hoặc tổ chức tôn giáo.',
      'qualified_alternatives':'Giấy chứng nhận không phải điều kiện duy nhất: các trường hợp thuộc khoản 1 Điều 95 được bồi thường về đất khi có một trong các điều kiện tại khoản 2 Điều 95, như có Giấy chứng nhận hoặc có quyết định giao đất của cơ quan nhà nước có thẩm quyền. Cộng đồng dân cư là nhóm đối tượng ở khoản 1 Điều 95, không phải một giấy tờ thay thế trong khoản 2 Điều 95.'}[variant]
    state={'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000',message='Giấy chứng nhận có phải điều kiện duy nhất để được bồi thường về đất không?'),
           'budget':Budget(),'release':payload,'as_of':date(2024,8,2),'plan':Plan(),
           'evidence':[Evidence(document=doc,chunk=c,applicability='current') for c in doc.chunks],
           'draft':Draft(status='answered',claims=[Claim(text=text,citation_ids=[c.id for c in doc.chunks])]),'trace':[],'emit':noop}
    agent=Agent(store,FakeProvider(settings,verification=Verification(supported_claim_indexes=[0])))
    await agent.verify(state);await agent.finish(state)
    assert bool(state['result'].verified_claims) is expected
