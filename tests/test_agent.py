from datetime import date, timedelta

import pytest

from landlaw.agent import Agent, Plan, ToolCall, Verification, applicability
from landlaw.models import ChatRequest, Claim, Draft
from landlaw.provider import Budget, BudgetExceeded, ProviderUnavailable
from landlaw.security import utcnow
from landlaw.store import RateLimited
from conftest import document, release, session, supplied_synthesis_fixture


def test_pdf_citation_maps_global_chunk_index_to_exact_attachment_and_physical_page():
    from landlaw.agent import citation_source_url
    from landlaw.models import Evidence, SourceFile
    doc = document(source_files=[
        SourceFile(url='https://datafiles.chinhphu.vn/first.pdf', checksum='a', first_page_index=0, last_page_index=1),
        SourceFile(url='https://datafiles.chinhphu.vn/second.pdf', checksum='b', first_page_index=2, last_page_index=4)])
    chunk = doc.chunks[0].model_copy(update={'id':'law-2-0-0', 'page':1})
    assert citation_source_url(Evidence(document=doc, chunk=chunk)) == 'https://datafiles.chinhphu.vn/second.pdf#page=1'
    assert citation_source_url(Evidence(document=doc, chunk=chunk.model_copy(update={'id':'law-0-0-0', 'page':2}))) == 'https://datafiles.chinhphu.vn/first.pdf#page=2'
    assert citation_source_url(Evidence(document=doc.model_copy(update={'source_files':[]}), chunk=chunk)) is None
    assert citation_source_url(Evidence(document=doc, chunk=chunk.model_copy(update={'id':'invalid-id'}))) is None


def test_adding_article_7a_does_not_amend_the_existing_article_7():
    from landlaw.agent import relation_may_affect
    from landlaw.models import Evidence, Relation
    doc = document()
    evidence = Evidence(document=doc, chunk=doc.chunks[0].model_copy(update={'locator':'Điều 7'}))
    relation = Relation(source_id='amendment', target_id=doc.id, type='amends',
        source_locator='Điều 2', target_locators=['Điều 7a'], target_locators_complete=True,
        source_url='https://vanban.chinhphu.vn/', explanation='Adds Article 7a, leaving Article 7 unaffected')
    assert not relation_may_affect(relation, doc.id, [evidence])
    new_article = evidence.model_copy(update={'chunk':evidence.chunk.model_copy(update={'locator':'Điều 7a'})})
    assert relation_may_affect(relation, doc.id, [new_article])


class FakeProvider:
    """Explicit dependency injection for tests; never registered in the application."""
    configured = True
    def __init__(self, settings, draft=None, verification=None, failure=None):
        self.settings = settings
        self.draft = draft or Draft(status="answered", summary="Đã đối chiếu căn cứ.", claims=[Claim(text="Cần kiểm tra điều kiện theo hồ sơ.", citation_ids=["law-1"])])
        self.verification = verification or Verification(supported_claim_indexes=[0])
        self.failure = failure
    async def generate(self, schema, instruction, payload, budget):
        budget.llm()
        if self.failure:
            raise self.failure
        if schema is Plan:
            return Plan(tools=[ToolCall(name="search_law", query="bồi thường thu hồi đất")])
        if schema is Draft:
            return self.draft
        from landlaw.agent import SupportingSpan
        spans=[SupportingSpan(claim_index=i,citation_id=cid,span_id=span['span_id'])
               for i,c in enumerate(payload['draft']['claims']) for cid in c['citation_ids']
               for span in payload['source_spans'] if span['citation_id']==cid]
        return self.verification.model_copy(update={'supporting_spans':spans})
    async def embed(self, *args, **kwargs):
        raise ProviderUnavailable("Embedding offline in test")


async def noop(_):
    pass


async def test_related_document_reads_obey_tool_budget_and_keep_unaffected_articles(store,settings,monkeypatch):
    from landlaw.models import Relation
    from landlaw.provider import Budget
    original=document()
    original.chunks[0].locator='Điều 104'
    related=[document('amendment-'+str(i)) for i in range(20)]
    unrelated=document('unrelated')
    relations=[Relation(source_id=d.id,target_id=original.id,type='amends',
        target_locators=['Điều 104'],target_locators_complete=True,
        source_locator='Điều 1',source_url=d.url,explanation='Test amendment scope') for d in related]
    relations.append(Relation(source_id=unrelated.id,target_id=original.id,type='amends',
        target_locators=['Điều 182'],target_locators_complete=True,
        source_locator='Điều 1',source_url=unrelated.url,explanation='Unrelated test scope'))
    payload=release(store,[original,*related,unrelated],relations=[r.model_dump(mode='json') for r in relations])
    opened=[]
    real_open=store.open_document
    def tracked_open(doc_id,*args):
        opened.append(doc_id)
        return real_open(doc_id,*args)
    monkeypatch.setattr(store,'open_document',tracked_open)
    sid, _ = session(store)
    state={'request':ChatRequest(session_id=sid,message='Điều 104',mode='agentic'),
        'budget':Budget(),'release':payload,'plan':Plan(tools=[ToolCall(name='open_article',document_id='law',locator='Điều 104')]),
        'as_of':date(2026,10,12),'evidence':[],'rounds':0,'tool_notes':[],'trace':[],'emit':noop}
    result=await Agent(store,FakeProvider(settings)).tools(state)
    assert state['budget'].tool_calls == 12
    assert len(opened) <= 11
    assert 'unrelated' not in opened
    assert result['evidence'] and any(event.tool=='open_article' and event.document_ids!=['law'] for event in result['trace'])


async def test_historical_partial_repeal_keeps_operative_clause_before_future_replacement(store,settings):
    from landlaw.models import Relation
    original=document('original',document_number='38/2025/QĐ-UBND')
    amendment=document('amendment',document_number='10/2026/QĐ-UBND')
    operative=amendment.chunks[0].model_copy(update={'id':'operative','locator':'Điều 2',
        'text':'Điều 2. Bãi bỏ Điều 2 của Quyết định số 38/2025/QĐ-UBND.'})
    amendment.chunks=[amendment.chunks[0],operative]
    future=document('future',document_number='40/2026/QĐ-UBND')
    future.effective_from=date(2026,4,2)
    future.chunks[0].text='Quyết định này có hiệu lực ngày 02/04/2026 và thay thế các quyết định cũ.'
    relations=[Relation(source_id=future.id,target_id=amendment.id,type='replaces',
        source_locator='Điều 1',source_url=future.url,explanation='Replacement starts after the question date'),
        Relation(source_id=amendment.id,target_id=original.id,type='repeals',source_locator='Điều 2',
        target_locators=['Điều 2'],target_locators_complete=True,source_url=amendment.url,
        explanation='Only Article 2 is repealed at the question date')]
    payload=release(store,[original,amendment,future],relations=[r.model_dump(mode='json') for r in relations])
    sid,_=session(store);agent=Agent(store,FakeProvider(settings))
    state={'request':ChatRequest(session_id=sid,message='10/2026/QĐ-UBND bãi bỏ toàn bộ 38/2025/QĐ-UBND không?',mode='agentic'),
        'budget':Budget(),'release':payload,'plan':Plan(tools=[ToolCall(name='search_law',query='10/2026/QĐ-UBND bãi bỏ 38/2025/QĐ-UBND')]),
        'as_of':date(2026,1,20),'evidence':[],'rounds':0,'tool_notes':[],'trace':[],'emit':noop}
    hits=await agent.search(state,state['request'].message)
    assert hits[0].document.id!=future.id
    await agent.tools(state)
    settings.llm_provider='groq'
    passages,_=agent.prompt_context(state)
    assert any(p['citation_id']=='operative' for p in passages)
    assert passages[0]['document_id']!=future.id


async def test_partial_repeal_fact_requires_complete_scope_and_literal_source(store,settings):
    from landlaw.models import Relation
    source=document('source',document_number='10/2026/QĐ-UBND',
        text='Điều 2. Bãi bỏ Điều 2 Quyết định số 38/2025/QĐ-UBND.')
    source.chunks[0].locator='Điều 2'
    target=document('target',document_number='38/2025/QĐ-UBND')
    relation=Relation(source_id='source',target_id='target',type='repeals',source_locator='Điều 2',
        target_locators=['Điều 2'],target_locators_complete=True,source_url=source.url,explanation='Source checked partial repeal')
    payload=release(store,[source,target],relations=[relation.model_dump(mode='json')]);sid,_=session(store)
    class NoInference(FakeProvider):
        async def generate(self,*args):raise AssertionError('Verified repeal scope is read from the source, not inferred by a model')
    agent=Agent(store,NoInference(settings))
    result=await agent.run(ChatRequest(session_id=sid,mode='agentic',as_of=date(2026,1,20),
        message='10/2026/QĐ-UBND bãi bỏ toàn bộ 38/2025/QĐ-UBND hay một phần?'),noop)
    assert result.status=='answered' and result.llm_calls==0
    assert 'không phải toàn bộ' in result.content and len(result.verified_claims)==1
    from landlaw.models import Evidence
    state={'request':ChatRequest(session_id=sid,message='10/2026/QĐ-UBND bãi bỏ toàn bộ 38/2025/QĐ-UBND không?'),
        'release':payload,'evidence':[Evidence(document=source,chunk=source.chunks[0],applicability='current')]}
    payload['relations'][0]['target_locators_complete']=False
    assert agent.partial_repeal(state) is None
    payload['relations'][0]['target_locators_complete']=True
    state['evidence'][0].chunk=source.chunks[0].model_copy(update={'text':'Điều 2. Nội dung khác, không xác định phạm vi.'})
    assert agent.partial_repeal(state) is None


def test_as_of_observation_is_distinct_from_claimed_commencement_date():
    from landlaw.agent import claim_source_dates
    assert claim_source_dates('Văn bản không còn hiệu lực vào ngày 12/10/2026.',date(2026,10,12))==set()
    assert claim_source_dates('Văn bản có hiệu lực từ ngày 12/10/2026.',date(2026,10,12))=={date(2026,10,12)}
    assert claim_source_dates('Tại ngày 12/10/2026, văn bản có hiệu lực từ 12/10/2026.',date(2026,10,12))=={date(2026,10,12)}
    assert claim_source_dates('Tại ngày 12/10/2026, văn bản có hiệu lực từ 02/04/2026.',date(2026,10,12))=={date(2026,4,2)}


def test_effective_date_parser_distinguishes_observed_negative_status_and_true_commencement():
    from landlaw.agent import claim_effective_dates
    as_of=date(2026,10,12)
    text='Văn bản không còn hiệu lực vào ngày 12/10/2026; văn bản thay thế có hiệu lực từ 02/04/2026.'
    assert claim_effective_dates(text,as_of)=={date(2026,4,2)}
    assert claim_effective_dates('Văn bản có hiệu lực từ ngày 12/10/2026.',as_of)=={as_of}
    assert claim_effective_dates('Văn bản không còn hiệu lực vào ngày 11/10/2026.',as_of)=={date(2026,10,11)}
    assert claim_effective_dates('Văn bản có hiệu lực từ 12/10/2026 và không còn hiệu lực vào ngày 12/10/2026.',as_of)=={as_of}


def test_effectivity_clause_does_not_inherit_replaced_act_issue_dates():
    from landlaw.agent import source_effective_dates
    text='Điều 2. Quyết định này có hiệu lực thi hành kể từ ngày 02 tháng 4 năm 2026 và thay thế Quyết định 56/2024 ngày 06/9/2024.'
    assert source_effective_dates(text)=={date(2026,4,2)}


def test_issued_date_is_not_misclassified_as_commencement_in_the_same_claim():
    from landlaw.agent import claim_effective_dates, claim_source_dates
    text='Quyết định 56/2024 ngày 06/9/2024 hết hiệu lực từ ngày 02 tháng 4 năm 2026.'
    assert claim_effective_dates(text)=={date(2026,4,2)}
    assert claim_source_dates(text,date(2026,10,12))=={date(2024,9,6),date(2026,4,2)}
    assert claim_effective_dates('Văn bản có hiệu lực từ 03/04/2026.')=={date(2026,4,3)}


async def test_commencement_clause_does_not_exclude_all_historical_files(store,settings):
    law=document(text='Điều 2. Quyết định về bồi thường khi thu hồi đất này có hiệu lực thi hành kể từ ngày 02 tháng 4 năm 2026.')
    release(store,[law])
    sid,_=session(store)
    draft=Draft(status='answered',summary='',claims=[Claim(kind='applicability',
        text='Quyết định có hiệu lực từ 02/04/2026 và không áp dụng cho các hồ sơ được xử lý trước ngày đó.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft=draft)).run(ChatRequest(
        session_id=sid,message='Hồ sơ cũ có áp dụng chính sách mới không?',as_of=date(2026,3,1)),noop)
    assert result.status=='insufficient_evidence' and result.verified_claims==[]
    assert any('chuyển tiếp' in event.summary for event in result.trace)


async def test_verifier_cannot_expand_partial_repeal_or_infer_universal_practice(store,settings):
    law=document(text='Điều 2. Bãi bỏ Điều 2 Quyết định số 38/2025/QĐ-UBND.')
    release(store,[law]);sid,_=session(store)
    draft=Draft(status='answered',summary='',claims=[
        Claim(kind='applicability',text='Bãi bỏ Điều 2 và một số khoản khác của Quyết định 38/2025/QĐ-UBND.',citation_ids=['law-1']),
        Claim(kind='applicability',text='Việc bãi bỏ thường diễn ra theo từng khoản, không toàn văn.',citation_ids=['law-1'])])
    provider=FakeProvider(settings,draft=draft,verification=Verification(supported_claim_indexes=[0,1]))
    result=await Agent(store,provider).run(ChatRequest(session_id=sid,message='Văn bản bị bãi bỏ toàn bộ không?',mode='agentic'),noop)
    assert result.status=='insufficient_evidence' and result.verified_claims==[]


async def test_repeal_cannot_be_attributed_to_a_different_act_even_if_model_approves(store,settings):
    law=document(document_number='38/2025/QĐ-UBND',
        text='Điều 3. Bãi bỏ khoản 3 Điều 3, Điều 23 của Quy định ban hành kèm Quyết định số 56/2024/QĐ-UBND.')
    release(store,[law]);sid,_=session(store)
    draft=Draft(status='answered',summary='',claims=[Claim(kind='applicability',
        text='Quyết định 10/2026/QĐ-UBND bãi bỏ khoản 3 Điều 3 và Điều 23 của Quyết định 38/2025/QĐ-UBND.',
        citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft=draft)).run(ChatRequest(session_id=sid,
        message='Điều 3 của 38/2025/QĐ-UBND bãi bỏ những gì?',mode='agentic'),noop)
    assert result.status=='insufficient_evidence' and not result.verified_claims
    assert any('số văn bản' in event.summary for event in result.trace)


def test_prompt_keeps_passages_and_deduplicates_document_legal_metadata(store,settings):
    from landlaw.models import Evidence
    law=document()
    relation={'source_id':'amendment','target_id':'law','type':'amends','target_locators':['Điều 1']}
    second=law.chunks[0].model_copy(update={'id':'law-2','text':'Đoạn chứng cứ thứ hai.'})
    state={'evidence':[Evidence(chunk=law.chunks[0],document=law),Evidence(chunk=second,document=law)],
        'release':{'documents':[law.model_dump(mode='json')],'relations':[relation]}}
    agent=Agent(store,FakeProvider(settings))
    passages,documents=agent.prompt_context(state)
    assert [p['citation_id'] for p in passages]==['law-1','law-2']
    assert passages[1]['text']==second.text and len(documents)==1
    assert dict(zip(documents[0]['legal_relation_fields'],documents[0]['legal_relations'][0]))['target_locators']==['Điều 1']
    assert all('legal_relations' not in passage for passage in passages)
    selected,metadata=agent.prompt_context(state,{'law-2'})
    assert len(selected)==len(metadata)==1 and selected[0]['citation_id']=='law-2'


def test_parent_context_retains_clause_continuation_without_duplicate_children(store,settings):
    from landlaw.models import Evidence
    law=document()
    first=law.chunks[0].model_copy(update={'id':'law-a','parent_id':'law-a-parent',
        'text':'Điều 12. Điều kiện. 1. Đối tượng được quy định tại điểm a, b. '})
    second=first.model_copy(update={'id':'law-b',
        'text':'2. Trường hợp thuộc khoản 1 được hỗ trợ khi có một trong các giấy tờ sau đây.'})
    parent=first.model_copy(update={'id':'law-a-parent','parent_id':None,
        'text':first.text+second.text,'locator':'Điều 1 · ngữ cảnh'})
    state={'evidence':[Evidence(chunk=c,document=law) for c in [first,second,parent]],
        'release':{'documents':[law.model_dump(mode='json')],'relations':[]}}
    agent=Agent(store,FakeProvider(settings))
    passages,_=agent.prompt_context(state)
    assert [p['citation_id'] for p in passages]==[parent.id]
    assert first.text in passages[0]['text'] and second.text in passages[0]['text']
    # A verifier must see the exact citation selected by the draft, even when
    # it is an incomplete child; deduplication must not silently repair proof.
    selected,_=agent.prompt_context(state,{second.id})
    assert selected[0]['citation_id']==second.id and selected[0]['text']==second.text


async def test_unlocated_legal_question_searches_original_question_without_speculating_article(store,settings):
    payload=release(store)
    question='Khi chuyển cơ sở vì thu hồi đất, chi phí tháo dỡ được xem xét thế nào?'
    provider=FakeProvider(settings)
    async def unexpected(*args,**kwargs):raise AssertionError('No speculative planner call needed')
    provider.generate=unexpected
    state={'request':ChatRequest(session_id='00000000-0000-0000-0000-000000000000',message=question),
        'release':payload,'budget':Budget(),'trace':[],'emit':noop,'history':[]}
    await Agent(store,provider).plan(state)
    assert state['plan'].tools==[ToolCall(name='search_law',query=question)]
    assert state['budget'].llm_calls==0


async def test_primary_parent_survives_full_secondary_evidence_on_retry(store,settings,monkeypatch):
    from landlaw.models import Evidence
    docs=[document(f'new-{i}') for i in range(8)]
    previous=[document(f'old-{i}') for i in range(8)]
    first=docs[0].chunks[0]
    first.parent_id='new-0-parent'
    parent=first.model_copy(update={'id':first.parent_id,'parent_id':None,
        'text':first.text+' Điều kiện tiếp theo phải được đọc cùng đoạn đầu.'})
    docs[0].chunks.append(parent)
    payload=release(store,docs+previous)
    monkeypatch.setattr(store,'search',lambda *args:[Evidence(chunk=d.chunks[0],document=d) for d in docs])
    state={'request':ChatRequest(session_id='0'*32,message='Điều kiện bồi thường?'),
        'release':payload,'plan':Plan(),'budget':Budget(),'as_of':date(2024,8,2),
        'verification':Verification(followup_query='căn cứ bổ sung'),
        'evidence':[Evidence(chunk=d.chunks[0],document=d) for d in previous],
        'rounds':1,'tool_notes':[],'trace':[],'emit':noop}
    await Agent(store,FakeProvider(settings)).tools(state)
    assert len(state['evidence'])==16
    assert parent.id in {item.chunk.id for item in state['evidence']}
    assert [e.document.id for e in state['evidence'][:8]]==[d.id for d in docs]


def test_groq_context_selects_complete_passages_and_never_cites_omitted_text(store,settings):
    from landlaw.models import Evidence
    import json
    law=document()
    chunks=[law.chunks[0].model_copy(update={'id':f'law-{i}','text':('Điều kiện pháp lý đầy đủ. '*90)+str(i)})
            for i in range(8)]
    state={'evidence':[Evidence(chunk=c,document=law) for c in chunks],
           'release':{'documents':[law.model_dump(mode='json')],'relations':[]}}
    agent=Agent(store,FakeProvider(settings.model_copy(update={'llm_provider':'groq'})))
    passages,documents=agent.prompt_context(state)
    assert 0<len(passages)<8
    assert len(json.dumps([passages,documents],ensure_ascii=False))<=7000
    assert all(p['text']==next(c.text for c in chunks if c.id==p['citation_id']) for p in passages)
    # Verification can always reopen every cited full passage regardless of the
    # synthesis budget, so unsupported parts cannot disappear during checking.
    selected,_=agent.prompt_context(state,{c.id for c in chunks})
    assert len(selected)==8 and len(state['evidence'])==8


async def test_explicit_effectivity_question_routes_to_real_search_without_planner_call(store,settings):
    law=document(document_number='31/2024/QH15')
    payload=release(store,[law])
    provider=FakeProvider(settings)
    async def unexpected(*args,**kwargs):raise AssertionError('Unnecessary planner request')
    provider.generate=unexpected
    state={'request':ChatRequest(session_id='00000000-0000-0000-0000-000000000000',
        message='31/2024/QH15 còn hiệu lực không?',mode='agentic'),
        'release':payload,'budget':Budget(),'trace':[],'emit':noop,'history':[]}
    await Agent(store,provider).plan(state)
    assert state['plan'].tools[0].name=='search_law' and state['budget'].llm_calls==0


def test_context_prioritizes_operative_replacement_over_old_preamble(store,settings):
    from landlaw.models import Evidence
    old=document('old',text='Căn cứ Luật năm 2024, ban hành Quyết định 56/2024.',document_number='56/2024/QĐ-UBND')
    new=document('new',text='Điều 2. Có hiệu lực từ ngày 02/04/2026 và thay thế Quyết định 56/2024.',
                 document_number='40/2026/QĐ-UBND')
    state={'request':ChatRequest(session_id='00000000-0000-0000-0000-000000000000',
        message='56/2024/QĐ-UBND còn hiệu lực không, văn bản nào thay thế?'),
        'evidence':[Evidence(chunk=old.chunks[0],document=old),Evidence(chunk=new.chunks[0],document=new)],
        'release':{'documents':[old.model_dump(mode='json'),new.model_dump(mode='json')],'relations':[]}}
    agent=Agent(store,FakeProvider(settings.model_copy(update={'llm_provider':'groq'})))
    passages,_=agent.prompt_context(state)
    assert passages[0]['citation_id']=='new-1' and passages[0]['text']==new.chunks[0].text


def test_reference_in_long_article_reaches_prompt_before_similar_later_clauses(store,settings):
    from landlaw.models import Evidence
    law=document(document_number='151/2025/NĐ-CP')
    first=law.chunks[0].model_copy(update={'locator':'Điều 5','text':
        'Điều 5. Thẩm quyền chuyển cho Chủ tịch UBND cấp xã. '
        'd) Phê duyệt phương án bồi thường theo điểm c khoản 3 Điều 87 Luật Đất đai.'})
    similar=first.model_copy(update={'id':'later','text':
        'Phê duyệt phương án bồi thường theo khoản 3 Điều 3 Nghị định 88/2024/NĐ-CP.'})
    state={'request':ChatRequest(session_id='0'*32,message=
        'Điều 5 Nghị định 151/2025/NĐ-CP chuyển thẩm quyền ở điểm c khoản 3 Điều 87 cho ai?'),
        'evidence':[Evidence(chunk=similar,document=law),Evidence(chunk=first,document=law)],
        'release':{'documents':[law.model_dump(mode='json')],'relations':[]}}
    agent=Agent(store,FakeProvider(settings.model_copy(update={'llm_provider':'groq'})))
    passages,_=agent.prompt_context(state)
    assert passages[0]['citation_id']==first.id and passages[0]['text']==first.text
    assert 'later' not in {passage['citation_id'] for passage in passages}
    amendment=document('amendment',text='Điều 2. Sửa đổi điểm d khoản 1 Điều 5 của Nghị định 151/2025/NĐ-CP.')
    state['evidence'].append(Evidence(chunk=amendment.chunks[0],document=amendment))
    state['release']['documents'].append(amendment.model_dump(mode='json'))
    state['release']['relations']=[{'source_id':'amendment','target_id':law.id,'type':'amends',
        'target_locators':['Điều 5'],'target_locators_complete':True,
        'source_url':str(amendment.url),'explanation':'Verified amendment to the requested article.'}]
    passages,_=agent.prompt_context(state)
    assert 'amendment-1' in {passage['citation_id'] for passage in passages}


async def test_future_immediate_application_states_only_verified_start_and_asks_case_facts(store,settings):
    law=document(text='Điều 2. Quyết định này có hiệu lực thi hành từ ngày 02/04/2026.',
                 document_number='40/2026/QĐ-UBND')
    law.effective_from=date(2026,4,2)
    release(store,[law]);sid,_=session(store)
    class Provider(FakeProvider):
        async def generate(self,schema,instruction,payload,budget):
            raise AssertionError('A literal source date and chronological comparison need no model inference')
    result=await Agent(store,Provider(settings)).run(ChatRequest(session_id=sid,
        message='Hồ sơ xét ngày 01/03/2026 có áp dụng ngay 40/2026/QĐ-UBND để tính quyền lợi không?',
        mode='agentic',as_of=date(2026,3,1)),noop)
    assert result.status=='clarification_needed' and len(result.verified_claims)==1
    assert 'chưa có hiệu lực tại ngày 01/03/2026' in result.content
    assert result.missing_facts and result.llm_calls==0


@pytest.mark.parametrize('question,status,facts',[
    ('Điều 95 có điều kiện bồi thường khi thu hồi đất nào?','answered',[]),
    ('Nhà tôi cần kiểm tra Điều 95 về điều kiện bồi thường khi thu hồi đất?','clarification_needed',['Ngày phê duyệt phương án của gia đình'])])
async def test_missing_tool_identifier_falls_back_and_never_becomes_public_question(store,settings,question,status,facts):
    law=document(document_number='31/2024/QH15',issued_on=date(2024,1,18))
    release(store,[law]);sid,_=session(store)
    class Provider(FakeProvider):
        async def generate(self,schema,instruction,payload,budget):
            if schema is Plan:
                budget.llm()
                return Plan(tools=[ToolCall(name='check_effectivity')],missing_facts=[
                    'document_id của văn bản','Ngày ban hành Luật 31/2024/QH15','Ngày phê duyệt phương án của gia đình'])
            return await super().generate(schema,instruction,payload,budget)
    result=await Agent(store,Provider(settings)).run(ChatRequest(session_id=sid,
        message=question),noop)
    assert result.verified_claims and result.status==status
    assert result.missing_facts==facts
    assert any('Không mở được' in event.summary for event in result.trace)
    assert result.tool_calls<=12 and result.llm_calls<=6


@pytest.mark.parametrize('span,citation,expected', [('law-1:span:0','law-1','answered'),
    ('invented:span:0','law-1','insufficient_evidence'),('law-1:span:0','other','insufficient_evidence')])
async def test_source_span_selection_is_exact_and_scoped_to_citation(store,settings,span,citation,expected):
    from landlaw.agent import SupportingSpan
    release(store)
    sid,_=session(store)
    class Provider(FakeProvider):
        async def generate(self,schema,instruction,payload,budget):
            if schema is Verification:
                budget.llm()
                return Verification(supported_claim_indexes=[0],supporting_spans=[SupportingSpan(
                    claim_index=0,citation_id=citation,span_id=span)])
            return await super().generate(schema,instruction,payload,budget)
    result=await Agent(store,Provider(settings)).run(ChatRequest(session_id=sid,message='Điều kiện bồi thường?'),noop)
    assert result.status==expected
    assert bool(result.citations)==(expected=='answered')


def test_clause_effective_date_does_not_change_the_whole_document():
    law = document()
    law.effective_from = date(2026,7,1)
    law.provision_validity = [{'locator':'khoản 4 Điều 8','effective_from':'2026-04-23','effective_to':None}]
    law.chunks[0].locator = 'Điều 8'
    assert applicability(law,date(2026,5,1)) == 'future'
    assert applicability(law,date(2026,5,1),law.chunks[0]) == 'provision_specific'
    law.chunks[0].locator = 'Điều 9'
    assert applicability(law,date(2026,5,1),law.chunks[0]) == 'future'
    law.effective_from = date(2024,12,20)
    law.provision_validity = [{'locator':'Điều 1 khoản 1 — kỳ áp dụng bảng giá','effective_from':'2024-12-20','effective_to':'2026-01-01'}]
    law.chunks[0].text = '[BẢNG / ĐƠN GIÁ — giữ đơn vị]\nSTT  Giá đất'
    assert applicability(law,date(2026,10,12),law.chunks[0]) == 'historical'
    assert applicability(law,date(2026,10,12)) == 'current'


def test_added_article_scope_does_not_apply_to_original_article():
    from landlaw.agent import relation_chunks
    law = document()
    original = law.chunks[0]
    original.locator = 'Điều 28'
    added = original.model_copy(update={'id':'law-added','locator':'Điều 28a'})
    law.chunks = [original, added]
    law.provision_validity = [{'locator':'khoản 1 Điều 28a','effective_from':'2024-08-01','effective_to':'2026-01-01'}]
    assert applicability(law,date(2026,10,12),original) == 'current'
    assert applicability(law,date(2026,10,12),added) == 'provision_specific'
    assert relation_chunks(law,'Điều 28') == [original]
    assert relation_chunks(law,'Điều 28a') == [added]


async def test_graph_calls_tools_and_verifies_before_answer(store, settings):
    release(store)
    sid, _ = session(store)
    events = []
    async def capture(event):
        events.append(event.step)
    result = await Agent(store, FakeProvider(settings)).run(ChatRequest(session_id=sid, message="Điều kiện bồi thường?"), capture)
    assert result.status == "answered"
    assert result.citations[0].id == "law-1"
    assert result.llm_calls == 2 and result.tool_calls >= 2
    assert events.index("synthesis") < events.index("verification")


async def test_invalid_citation_removed_not_rendered(store, settings):
    release(store)
    sid, _ = session(store)
    draft = Draft(status="answered", summary="Kết quả", claims=[Claim(text="Nội dung không hợp lệ", citation_ids=["hallucinated"])])
    result = await Agent(store, FakeProvider(settings, draft)).run(ChatRequest(session_id=sid, message="bồi thường"), noop)
    assert result.status == "insufficient_evidence"
    assert not result.citations and "Nội dung không hợp lệ" not in result.content


async def test_outside_scope_never_renders_medical_advice(store,settings):
    release(store)
    sid,_=session(store)
    draft=Draft(status='insufficient_evidence',summary='Ngoài phạm vi',out_of_scope=True,
        next_steps=['Uống thuốc không có căn cứ.'],missing_facts=['Triệu chứng?'])
    result=await Agent(store,FakeProvider(settings,draft)).run(ChatRequest(session_id=sid,message='Tư vấn chữa bệnh trong dự án thu hồi đất?',mode='agentic'),noop)
    assert 'ngoài phạm vi' in result.content and 'Uống thuốc' not in result.content and 'Triệu chứng' not in result.content


async def test_unverified_legal_claims_are_blocked(store, settings):
    law = document()
    law.applicability_verified = False
    release(store, [law])
    sid, _ = session(store)
    result = await Agent(store, FakeProvider(settings)).run(ChatRequest(session_id=sid, message="bồi thường"), noop)
    assert result.status == "insufficient_evidence" and not result.citations


async def test_stale_corpus_does_not_claim_current_law(store, settings):
    payload = release(store)
    payload["id"] = "old"
    payload["checked_at"] = (utcnow()-timedelta(days=8)).isoformat()
    store.stage(payload); store.publish("old")
    sid, _ = session(store)
    result = await Agent(store, FakeProvider(settings)).run(ChatRequest(session_id=sid, message="hiện nay bồi thường?"), noop)
    assert result.status == "insufficient_evidence" and not result.citations
    assert "quá bảy ngày" in result.content


@pytest.mark.parametrize('verification_fails', [False, True])
async def test_explicit_stale_generation_keeps_freshness_metadata_and_claim_verification(store, settings, verification_fails):
    settings.allow_stale_generation = True
    payload = release(store)
    payload['id'] = 'unreviewed-snapshot'
    payload['checked_at'] = (utcnow()-timedelta(days=8)).isoformat()
    store.stage(payload); store.publish(payload['id'])
    verification = Verification(supported_claim_indexes=[], issues=['Unsupported claim']) if verification_fails else None
    sid, _ = session(store)
    result = await Agent(store, FakeProvider(settings, verification=verification)).run(
        ChatRequest(session_id=sid, message='bồi thường thu hồi đất'), noop)
    assert result.llm_calls > 0
    assert 'Nguồn chưa được rà soát cập nhật' not in result.content
    assert 'nội dung tham khảo từ snapshot' not in result.content
    assert not store.source_fresh(store.release())
    assert store.release()['checked_at'] == payload['checked_at']
    if verification_fails:
        assert result.status == 'insufficient_evidence' and not result.verified_claims and not result.citations
    else:
        assert result.status == 'answered' and result.verified_claims and result.citations


@pytest.mark.parametrize("failure,status", [(RateLimited(30), "limited"), (BudgetExceeded(), "limited"), (ProviderUnavailable("API unavailable"), "error")])
async def test_provider_failures_return_explicit_status(store, settings, failure, status):
    release(store)
    sid, _ = session(store)
    result = await Agent(store, FakeProvider(settings, failure=failure)).run(ChatRequest(session_id=sid, message="bồi thường"), noop)
    assert result.status == status


async def test_retry_is_bounded(store, settings):
    release(store)
    sid, _ = session(store)
    verification = Verification(needs_more_evidence=True, followup_query="bồi thường", issues=["Thiếu căn cứ"])
    result = await Agent(store, FakeProvider(settings, verification=verification)).run(ChatRequest(session_id=sid, message="bồi thường"), noop)
    assert result.llm_calls <= 6 and result.tool_calls <= 12
    assert result.status == "insufficient_evidence"


def test_temporal_boundaries_and_historical_documents():
    old = document(effective_to=date(2026, 4, 2))
    assert applicability(old, date(2026, 4, 1)) == "current"
    assert applicability(old, date(2026, 4, 2)) == "historical"
    assert applicability(old, date(2023, 1, 1)) == "future"


async def test_partial_repeal_requires_affected_amendment_without_invalidating_other_article(store, settings):
    original = document()
    amendment = document('change', text='Điều 2. Bãi bỏ riêng Điều 1 của văn bản cũ.')
    relation = {'source_id': 'change', 'target_id': 'law', 'type': 'repeals', 'locator': 'Điều 2',
                'source_locator': 'Điều 2', 'target_locators': ['Điều 1'], 'target_locators_complete': True,
                'source_url': 'https://vanban.chinhphu.vn/?docid=2', 'explanation': 'Chỉ bãi bỏ Điều 1.'}
    release(store, [original, amendment], relations=[relation])
    sid, _ = session(store)
    result = await Agent(store, FakeProvider(settings)).run(ChatRequest(session_id=sid, message='bồi thường'), noop)
    assert result.status == 'insufficient_evidence' and not result.citations
    assert applicability(original, date(2026, 10, 12)) == 'current'
    original.chunks[0].locator = 'Điều 3'
    release(store, [original, amendment], release_id='other-article', relations=[relation])
    result = await Agent(store, FakeProvider(settings)).run(ChatRequest(session_id=sid, message='bồi thường'), noop)
    assert result.status == 'answered'


def test_later_clause_commencement_is_not_treated_as_whole_article_current():
    law=document(provision_validity=[{'locator':'Điểm a khoản 3 Điều 10','effective_from':'2027-01-01'}])
    law.chunks[0].locator='Điều 10'
    assert applicability(law,date(2026,10,12),law.chunks[0])=='provision_specific'
    law.chunks[0].locator='Điều 11'
    assert applicability(law,date(2026,10,12),law.chunks[0])=='current'


async def test_conditional_override_does_not_blanket_repeal_original(store,settings):
    original=document()
    special=document('special',text='Điều 13. Nếu cùng vấn đề có quy định khác nhau thì áp dụng chính sách này.')
    relation={'source_id':'special','target_id':'law','type':'overrides','source_locator':'Điều 13',
              'source_url':str(special.url),'explanation':'Ưu tiên có điều kiện, không bãi bỏ luật gốc.'}
    release(store,[original,special],relations=[relation])
    assert store.relations('law')[0].type=='overrides'
    sid,_=session(store)
    result=await Agent(store,FakeProvider(settings)).run(ChatRequest(session_id=sid,message='bồi thường'),noop)
    assert result.status=='answered'
    assert applicability(original,date(2026,10,12))=='current'


async def test_citation_quote_must_come_from_the_cited_passage(store,settings):
    from landlaw.agent import SupportingQuote
    release(store)
    sid,_=session(store)
    class BadQuote(FakeProvider):
        async def generate(self,schema,instruction,payload,budget):
            if schema is Verification:
                budget.llm()
                return Verification(supported_claim_indexes=[0],supporting_quotes=[SupportingQuote(
                    claim_index=0,citation_id='law-1',quote='Fabricated text not present in the cited official passage.')])
            return await super().generate(schema,instruction,payload,budget)
    result=await Agent(store,BadQuote(settings)).run(ChatRequest(session_id=sid,message='bồi thường'),noop)
    assert result.status=='insufficient_evidence' and not result.citations
    assert any(e.step=='repair' for e in result.trace)


async def test_authority_cannot_drop_the_chairperson(store,settings):
    text='Điều 1. Thẩm quyền chuyển giao cho Chủ tịch Ủy ban nhân dân cấp xã thực hiện.'
    release(store,[document(text=text)])
    sid,_=session(store)
    draft=Draft(status='answered',summary='Kết quả',claims=[Claim(
        text='Thẩm quyền chuyển giao cho Ủy ban nhân dân cấp xã thực hiện.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft)).run(ChatRequest(session_id=sid,message='thẩm quyền'),noop)
    assert result.status=='insufficient_evidence' and not result.verified_claims


async def test_retry_prioritizes_new_evidence_over_a_full_previous_context(store,settings,monkeypatch):
    from landlaw.models import Evidence
    from landlaw.agent import SupportingQuote
    docs=[document(f'old-{i}') for i in range(24)]+[document('new')]
    release(store,docs)
    sid,_=session(store)
    def search(query,*args):
        selected=[docs[-1]] if query=='new' else docs[int(query)*8:(int(query)+1)*8]
        return [Evidence(chunk=d.chunks[0],document=d) for d in selected]
    monkeypatch.setattr(store,'search',search)
    class Fresh(FakeProvider):
        async def generate(self,schema,instruction,payload,budget):
            budget.llm()
            if schema is Plan:
                return Plan(tools=[ToolCall(name='search_law',query=str(i)) for i in range(3)])
            if schema is Draft:
                return Draft(status='answered',summary='Kết quả',claims=[Claim(text='Điều kiện được kiểm tra theo hồ sơ.',citation_ids=['new-1'])])
            if any(e['document_id']=='new' for e in payload['evidence']):
                citation=next(e['citation_id'] for e in payload['evidence'] if e['document_id']=='new')
                return Verification(supported_claim_indexes=[0],supporting_quotes=[SupportingQuote(
                    claim_index=0,citation_id=citation,quote=docs[-1].chunks[0].text)])
            return Verification(needs_more_evidence=True,followup_query='new',issues=['Cần chứng cứ mới'])
    result=await Agent(store,Fresh(settings)).run(ChatRequest(session_id=sid,message='Điều 95 về bồi thường'),noop)
    assert result.status=='answered' and result.citations[0].id=='new-1'
    assert result.llm_calls<=6 and result.tool_calls<=12


async def test_issued_date_does_not_prove_effective_date(store, settings):
    law=document(text='Hà Nội, ngày 18 tháng 01 năm 2026. Quyết định ban hành quy định bồi thường.')
    release(store,[law])
    sid,_=session(store)
    draft=Draft(status='answered',summary='Kết quả',claims=[Claim(kind='applicability',
        text='Quyết định có hiệu lực từ ngày 18/01/2026.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft)).run(ChatRequest(session_id=sid,message='ngày hiệu lực?'),noop)
    assert result.status=='insufficient_evidence' and not result.verified_claims


async def test_date_cannot_be_borrowed_from_a_different_passage(store, settings):
    release(store,[document(text='Điều 1. Chuyển giao thẩm quyền thực hiện thủ tục đất đai.')])
    sid,_=session(store)
    draft=Draft(status='answered',summary='Kết quả',claims=[Claim(kind='applicability',
        text='Quy định có hiệu lực từ ngày 01 tháng 7 năm 2025.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft)).run(ChatRequest(session_id=sid,message='hiệu lực?'),noop)
    assert not result.verified_claims


def test_omitted_quote_spans_must_be_verbatim_in_order_in_the_same_passage():
    from landlaw.agent import quote_matches
    heading='Thẩm quyền chuyển giao cho Chủ tịch Ủy ban nhân dân cấp xã'
    clause='d) Quyết định phê duyệt phương án bồi thường, hỗ trợ, tái định cư;'
    text=heading+' a) Nội dung khác; b) Nội dung khác; '+clause
    assert quote_matches(heading+' ... '+clause,text)
    assert not quote_matches(clause+' ... '+heading,text)
    assert not quote_matches(heading+' ... '+'d) Tất cả hộ dân được bồi thường;',text)
    assert not quote_matches(heading+' ... '+clause,heading)


async def test_missing_tool_document_recovers_with_corpus_search(store,settings):
    release(store)
    sid,_=session(store)
    class Missing(FakeProvider):
        async def generate(self,schema,instruction,payload,budget):
            if schema is Plan:
                budget.llm()
                return Plan(tools=[ToolCall(name='check_effectivity',document_id='missing-history')])
            return await super().generate(schema,instruction,payload,budget)
    result=await Agent(store,Missing(settings)).run(ChatRequest(session_id=sid,message='bồi thường thu hồi đất'),noop)
    assert result.status=='answered' and result.citations[0].id=='law-1'
    assert any(e.tool=='search_law' for e in result.trace)
    assert result.tool_calls<=12


async def test_real_workflow_timeout_cancels_the_pending_provider(store,settings):
    import asyncio
    release(store)
    sid,_=session(store)
    settings.turn_timeout_seconds=1
    cancelled=[]
    class Slow(FakeProvider):
        async def generate(self,*args):
            try:await asyncio.sleep(100)
            finally:cancelled.append(True)
    result=await Agent(store,Slow(settings)).run(ChatRequest(session_id=sid,message='bồi thường'),noop)
    assert result.status=='error' and 'quá thời gian' in result.content
    assert cancelled and result.elapsed_ms<2500


async def test_effectivity_citation_is_aligned_before_semantic_verification(store,settings):
    from landlaw.models import Chunk
    from landlaw.security import digest
    law=document(text='Hà Nội, ngày 18 tháng 01 năm 2026. Quyết định ban hành quy định bồi thường.')
    text='Điều 2. Quyết định bồi thường này có hiệu lực thi hành kể từ ngày 18 tháng 01 năm 2026.'
    law.chunks.append(Chunk(id='law-2',document_id='law',text=text,locator='Điều 2',checksum=digest(text)))
    release(store,[law]);sid,_=session(store)
    draft=Draft(status='answered',summary='Kết quả',claims=[Claim(kind='applicability',
        text='Quyết định có hiệu lực thi hành từ ngày 18/01/2026.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft)).run(ChatRequest(session_id=sid,message='ngày hiệu lực bồi thường?'),noop)
    assert result.status=='answered' and result.citations[0].id=='law-2'


async def test_applicability_label_cannot_hide_future_entitlement(store,settings):
    from landlaw.security import local_date
    law=document(text='Quy định này có hiệu lực từ năm sau. Hộ đủ điều kiện được hỗ trợ 5 triệu đồng.')
    law.effective_from=local_date()+timedelta(days=10)
    release(store,[law]);sid,_=session(store)
    draft=Draft(status='answered',summary='Kết quả',claims=[Claim(kind='applicability',
        text='Hộ đủ điều kiện được hỗ trợ 5 triệu đồng.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft)).run(ChatRequest(session_id=sid,message='hỗ trợ bồi thường?'),noop)
    assert not result.verified_claims


def test_tool_exhaustion_repairs_existing_evidence_without_retrieval_overflow():
    from landlaw.provider import Budget
    budget=Budget(llm_calls=3,tool_calls=12)
    state={'budget':budget,'request':ChatRequest(session_id='t'*36,message='bồi thường'),
           'rounds':1,'draft':Draft(status='insufficient_evidence',summary='Thiếu căn cứ'),
           'verification':Verification(needs_more_evidence=True,issues=['Cần kiểm tra căn cứ']), 'repairs':0}
    assert Agent.route(state)=='repair'


@pytest.mark.parametrize('invalid', ['private_case','future_source','missing_target_number','partial_clause','unverified_target','different_expiry'])
def test_replacement_fact_never_expands_partial_scope_or_answers_private_entitlements(store,settings,invalid):
    from landlaw.models import Evidence
    old=document('old',document_number='56/2024/QĐ-UBND',effective_to=date(2026,4,2))
    new=document('new',document_number='40/2026/QĐ-UBND',
        text='Điều 2. Quyết định này có hiệu lực từ ngày 02/04/2026 và thay thế Quyết định 56/2024/QĐ-UBND.')
    new.effective_from=date(2026,4,2)
    relation={'source_id':new.id,'target_id':old.id,'type':'replaces','target_locators':[]}
    question='56/2024/QĐ-UBND còn hiệu lực ngày 12/10/2026 không?'
    if invalid=='private_case':question+=' Quyền lợi bồi thường của hồ sơ tôi là gì?'
    if invalid=='missing_target_number':new.chunks[0].text=new.chunks[0].text.replace('56/2024','99/2024')
    if invalid=='partial_clause':new.chunks[0].text=new.chunks[0].text.replace('thay thế Quyết định','thay thế Điều 2 của Quyết định')
    if invalid=='unverified_target':old.applicability_verified=False
    if invalid=='different_expiry':old.effective_to=date(2026,5,1)
    state={'request':ChatRequest(session_id='0'*32,message=question), 'as_of':date(2026,10,12),
        'evidence':[Evidence(chunk=new.chunks[0],document=new,applicability='future' if invalid=='future_source' else 'current')],
        'release':{'documents':[old.model_dump(mode='json'),new.model_dump(mode='json')],'relations':[relation]}}
    assert Agent.replacement_fact(state) is None


async def test_literal_whole_act_replacement_is_verified_without_model_inference(store,settings):
    old=document('old',document_number='56/2024/QĐ-UBND',effective_to=date(2026,4,2))
    new=document('new',document_number='40/2026/QĐ-UBND',
        text='Điều 2. Quyết định này có hiệu lực từ ngày 02/04/2026 và thay thế Quyết định 56/2024/QĐ-UBND.')
    new.effective_from=date(2026,4,2)
    new.chunks[0].locator='Điều 2'
    release(store,[old,new],relations=[{'source_id':new.id,'target_id':old.id,'type':'replaces',
        'locator':'Điều 2','source_url':str(new.url),'explanation':'Verified replacement of the whole act.'}])
    sid,_=session(store)
    class NoInference(FakeProvider):
        async def generate(self,*args,**kwargs):raise AssertionError('A literal replacement with verified dates needs no model inference')
    result=await Agent(store,NoInference(settings)).run(ChatRequest(session_id=sid,
        message='56/2024/QĐ-UBND còn hiệu lực ngày 12/10/2026 không, văn bản nào thay thế?',
        as_of=date(2026,10,12),mode='agentic'),noop)
    assert result.status=='answered' and result.llm_calls==0
    assert result.citations[0].id=='new-1' and len(result.verified_claims)==1
    assert '40/2026/QĐ-UBND' in result.content and '02/04/2026' in result.content


async def test_explicit_act_and_article_routes_to_bounded_read_without_planner(store,settings):
    doc=document(document_number='151/2025/NĐ-CP');payload=release(store,[doc])
    provider=FakeProvider(settings)
    async def unexpected(*args,**kwargs):raise AssertionError('An explicit known act/article needs no model planner')
    provider.generate=unexpected
    state={'request':ChatRequest(session_id='0'*32,message='Theo Điều 5 Nghị định 151/2025/NĐ-CP ai phê duyệt phương án?'),
        'release':payload,'budget':Budget(),'trace':[],'emit':noop,'history':[]}
    await Agent(store,provider).plan(state)
    call=state['plan'].tools[0]
    assert call.name=='open_article' and call.document_id==doc.id and call.locator=='Điều 5'


async def test_user_selected_project_routes_to_read_only_project_search(store,settings):
    payload=release(store);provider=FakeProvider(settings)
    async def unexpected(*args,**kwargs):raise AssertionError('The user already selected the project')
    provider.generate=unexpected
    state={'request':ChatRequest(session_id='0'*32,message='Nhà tôi có chắc được bồi thường không?',project='ring4'),
        'release':payload,'budget':Budget(),'trace':[],'emit':noop,'history':[]}
    await Agent(store,provider).plan(state)
    assert state['plan'].tools[0].name=='search_project' and state['budget'].llm_calls==0


async def test_invalid_planner_falls_back_only_to_bounded_read_and_still_verifies(store,settings):
    release(store);sid,_=session(store)
    class FormatFailure(FakeProvider):
        async def generate(self,schema,instruction,payload,budget):
            if schema is Plan:
                for _ in range(3):budget.llm()
                raise ProviderUnavailable('Invalid planning JSON',format_failure=True)
            return await super().generate(schema,instruction,payload,budget)
    result=await Agent(store,FormatFailure(settings)).run(ChatRequest(session_id=sid,message='Điều 95 có điều kiện bồi thường nào?'),noop)
    assert result.status=='answered' and result.llm_calls==5
    assert result.citations and any(e.step=='verification' for e in result.trace)
    assert any('Planner chưa trả đúng schema' in e.summary and e.tool=='search_law' for e in result.trace)
    assert all(e.tool in {None,'search_law','open_article','check_effectivity'} for e in result.trace)


async def test_planner_quota_does_not_trigger_fallback_or_unverified_answer(store,settings):
    release(store);sid,_=session(store)
    result=await Agent(store,FakeProvider(settings,failure=RateLimited(3600,source='provider'))).run(
        ChatRequest(session_id=sid,message='Điều 95 có điều kiện bồi thường nào?'),noop)
    assert result.status=='limited' and result.tool_calls==0 and not result.verified_claims
    assert result.retry_after==3600


@pytest.mark.parametrize('additional_origin', [True,False])
async def test_authority_origin_is_proven_by_requested_clause_not_combined_heading(store,settings,additional_origin):
    source=('Điều 5. Thẩm quyền của Ủy ban nhân dân cấp huyện, Chủ tịch Ủy ban nhân dân cấp huyện '
        'chuyển giao cho Chủ tịch Ủy ban nhân dân cấp xã. '
        '1. Thẩm quyền của Ủy ban nhân dân cấp huyện theo quy định của Luật Đất đai '
        'chuyển giao cho Chủ tịch Ủy ban nhân dân cấp xã thực hiện, bao gồm: '
        'd) Quyết định phê duyệt phương án bồi thường, hỗ trợ, tái định cư quy định tại điểm c khoản 3 Điều 87 Luật Đất đai.')
    release(store,[document(text=source)])
    sid,_=session(store)
    origin='Ủy ban nhân dân cấp huyện, Chủ tịch UBND cấp huyện' if additional_origin else 'Ủy ban nhân dân cấp huyện'
    draft=Draft(status='answered',claims=[Claim(text=f'Thẩm quyền tại điểm c khoản 3 Điều 87 chuyển từ {origin} sang Chủ tịch Ủy ban nhân dân cấp xã.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft=draft)).run(ChatRequest(session_id=sid,
        message='Thẩm quyền ở điểm c khoản 3 Điều 87 chuyển cho ai?',mode='agentic'),noop)
    assert result.status==('insufficient_evidence' if additional_origin else 'answered')
    if additional_origin:assert not result.verified_claims


def test_legal_relation_prose_cannot_crowd_required_statutory_passages_out_of_prompt(store,settings):
    from landlaw.models import Evidence
    law=document(text='Điều 95. Khoản 1 xác định đối tượng. Khoản 2 có giấy chứng nhận hoặc các giấy tờ khác.')
    other=law.chunks[0].model_copy(update={'id':'law-2','text':'Điều 95. Có quyết định giao đất hoặc giấy tờ nhận chuyển nhượng hợp pháp.'})
    relations=[{'source_id':f'guide-{i}','target_id':law.id,'type':'guides','source_locator':'Điều 3',
        'target_locators':['Điều 95'],'target_locators_complete':True,'source_url':str(law.url),
        'explanation':'Bối cảnh dài không thay thế căn cứ. '*150} for i in range(12)]
    state={'evidence':[Evidence(chunk=law.chunks[0],document=law),Evidence(chunk=other,document=law)],
        'release':{'documents':[law.model_dump(mode='json')],'relations':relations}}
    agent=Agent(store,FakeProvider(settings.model_copy(update={'llm_provider':'groq'})))
    passages,documents=agent.prompt_context(state)
    assert {p['citation_id'] for p in passages}=={'law-1','law-2'}
    fields=documents[0]['legal_relation_fields'];rows=documents[0]['legal_relations']
    assert len(rows)==12 and 'target_locators_complete' in fields
    assert rows[0][fields.index('target_locators')]==['Điều 95']
    assert all(p['text'] in {law.chunks[0].text,other.text} for p in passages)


@pytest.mark.parametrize('clause,expected', [('1','insufficient_evidence'),('2','answered')])
async def test_clause_attribution_cannot_use_another_numbered_clause(store,settings,clause,expected):
    source=('Điều 95. Điều kiện được bồi thường về đất. '
        '2. Các trường hợp quy định tại khoản 1 Điều này được bồi thường về đất khi có một trong các điều kiện sau đây: '
        'a) Có Giấy chứng nhận quyền sử dụng đất; b) Có quyết định giao đất của cơ quan nhà nước có thẩm quyền;')
    doc=document(text=source)
    doc.chunks[0].locator='Điều 95'
    release(store,[doc]);sid,_=session(store)
    draft=Draft(status='answered',claims=[Claim(text=f'Các trường hợp phải thuộc khoản 1 Điều này. Quyết định giao đất là điều kiện được quy định trong khoản {clause} Điều 95.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft=draft)).run(ChatRequest(session_id=sid,
        message='Giấy chứng nhận có phải điều kiện duy nhất theo Điều 95 không?',mode='agentic'),noop)
    assert result.status==expected


@pytest.mark.parametrize('qualification', ['', 'Các trường hợp phải thuộc đối tượng quy định tại khoản 1 Điều này. '])
async def test_alternative_conditions_preserve_eligibility_prerequisite(store,settings,qualification):
    source=('Điều 95. Điều kiện được bồi thường về đất. '
        '2. Các trường hợp quy định tại khoản 1 Điều này được bồi thường về đất khi có một trong các điều kiện sau đây: '
        'a) Có Giấy chứng nhận quyền sử dụng đất; b) Có quyết định giao đất của cơ quan nhà nước có thẩm quyền;')
    release(store,[document(text=source)]);sid,_=session(store)
    draft=Draft(status='answered',claims=[Claim(text=qualification+
        'Giấy chứng nhận không phải là điều kiện duy nhất để được bồi thường về đất.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft=draft)).run(ChatRequest(session_id=sid,
        message='Giấy chứng nhận có phải điều kiện duy nhất không?',mode='agentic'),noop)
    assert result.status == ('answered' if qualification else 'insufficient_evidence')
    if qualification:
        assert 'khoản 1' in result.verified_claims[0].text
    else:
        assert not result.verified_claims
        assert 'Lưu ý điều kiện áp dụng' not in result.content
        assert draft.claims[0].text.endswith('được bồi thường về đất.')
        assert any('cần nêu điều kiện về đối tượng' in e.summary for e in result.trace)


@pytest.mark.parametrize('letter', ['e','đ'])
async def test_legal_list_point_letters_cannot_be_renumbered(store,settings,letter):
    source=('Điều 108. Hỗ trợ khi Nhà nước thu hồi đất. 1. Hỗ trợ bao gồm: '
        'a) Hỗ trợ ổn định đời sống; đ) Hỗ trợ tái định cư đối với trường hợp đủ điều kiện; '
        'e) Hỗ trợ để tháo dỡ, phá dỡ, di dời.')
    release(store,[document(text=source)]);sid,_=session(store)
    draft=Draft(status='answered',claims=[Claim(text=f'Các nhóm hỗ trợ gồm a) Hỗ trợ ổn định đời sống; {letter}) Hỗ trợ tái định cư đối với trường hợp đủ điều kiện.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft=draft)).run(ChatRequest(session_id=sid,
        message='Các nhóm hỗ trợ khi thu hồi đất?',mode='agentic'),noop)
    assert result.status=='answered'
    text=result.verified_claims[0].text
    assert 'Hỗ trợ tái định cư đối với trường hợp đủ điều kiện.' in text
    if letter=='e':
        assert 'e)' not in text and 'a)' not in text
        assert any('bỏ ký hiệu liệt kê' in e.summary for e in result.trace)
    else:assert 'đ)' in text


async def test_explicit_wrong_legal_point_reference_is_not_silently_reformatted(store,settings):
    source=('Điều 108. Hỗ trợ khi Nhà nước thu hồi đất. '
        'a) Hỗ trợ ổn định đời sống; đ) Hỗ trợ tái định cư; e) Hỗ trợ tháo dỡ.')
    release(store,[document(text=source)]);sid,_=session(store)
    draft=Draft(status='answered',claims=[Claim(text='Điểm a) Hỗ trợ ổn định đời sống; điểm e) Hỗ trợ tái định cư.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft=draft)).run(ChatRequest(session_id=sid,
        message='Điểm nào hỗ trợ tái định cư?',mode='agentic'),noop)
    assert result.status=='insufficient_evidence' and not result.verified_claims


async def test_known_future_act_routes_to_evidence_without_inferred_private_rights(store,settings):
    doc=document(document_number='40/2026/QĐ-UBND',text='Quyết định này có hiệu lực thi hành từ ngày 02 tháng 4 năm 2026.')
    doc.effective_from=date(2026,4,2)
    release(store,[doc]);sid,_=session(store)
    class NoModel(FakeProvider):
        async def generate(self,*args):raise AssertionError('Future commencement must be proved from the source')
    result=await Agent(store,NoModel(settings)).run(ChatRequest(session_id=sid,
        message='Hồ sơ của tôi có áp dụng ngay Quyết định 40/2026/QĐ-UBND để tính quyền lợi không?',
        as_of=date(2026,3,1),mode='agentic'),noop)
    assert result.status=='clarification_needed' and result.llm_calls==0
    assert result.citations and 'chưa có hiệu lực' in result.content
    assert result.missing_facts and not any(c.kind=='legal_rule' for c in result.verified_claims)


@pytest.mark.parametrize('mode', ['agentic'])
async def test_personal_entitlement_guarantee_asks_for_file_without_applying_expired_law(store,settings,mode):
    old=document(text='Điều 19. Hộ có đủ điều kiện được mua căn hộ tái định cư.')
    old.effective_to=date(2026,4,2)
    release(store,[old]);sid,_=session(store)
    class NoModel(FakeProvider):
        async def generate(self,*args):raise AssertionError('Public law cannot prove this household entitlement')
    result=await Agent(store,NoModel(settings)).run(ChatRequest(session_id=sid,
        message='Nhà của tôi chắc chắn được một căn tái định cư đúng không?',as_of=date(2026,10,12),mode=mode),noop)
    assert result.status=='clarification_needed' and result.llm_calls==0
    assert not result.citations and not result.verified_claims
    assert len(result.missing_facts)==4 and 'chưa thể khẳng định' in result.content
    assert any('chuyển tiếp' in fact or 'đất ở' in fact for fact in result.missing_facts)


@pytest.mark.parametrize('question', [
    'Điều kiện tái định cư theo Luật Đất đai là gì?',
    'Có giấy chứng nhận là điều kiện duy nhất để được bồi thường đúng không?',
    'Nhà tôi cần kiểm tra hồ sơ nào để xác định điều kiện tái định cư?'])
def test_private_guarantee_guard_keeps_general_legal_and_document_guidance_queries(question):
    from landlaw.agent import private_entitlement_check
    assert not private_entitlement_check(question)


@pytest.mark.parametrize('timing', ['before_expiry','after_expiry','unrelated_transition','operative_transition'])
async def test_expired_legal_rule_requires_its_actual_operative_transition_even_if_model_approves(store,settings,timing):
    from landlaw.models import Evidence,Relation
    old=document('old',document_number='56/2024/QĐ-UBND',text='Điều 19. Hộ đủ điều kiện được mua một căn hộ tái định cư.')
    old.effective_to=date(2026,4,2)
    transition=document('new',text='Điều 31. Quy định chuyển tiếp: các phương án đã phê duyệt tiếp tục thực hiện.')
    transition.chunks[0].locator='Điều 31'
    relations=[Relation(source_id='new',target_id='old',type='transition',source_locator='Điều 31',
        source_url=transition.url,explanation='Reviewed transition to the old rule').model_dump(mode='json')]
    if timing=='unrelated_transition':relations[0]['source_locator']='Điều 99'
    payload=release(store,[old,transition],relations=relations)
    cited=['old-1']+(['new-1'] if timing in {'operative_transition','unrelated_transition'} else [])
    draft=Draft(status='answered',claims=[Claim(text='Hộ đủ điều kiện được mua một căn hộ tái định cư theo phương án cũ.',citation_ids=cited)])
    state={'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000',message='Quy định tái định cư nào áp dụng?',mode='agentic'),
        'budget':Budget(),'release':payload,'as_of':date(2026,4,1) if timing=='before_expiry' else date(2026,10,12),
        'evidence':[Evidence(chunk=old.chunks[0],document=old,applicability='current' if timing=='before_expiry' else 'historical'),
            Evidence(chunk=transition.chunks[0],document=transition,applicability='current')],
        'draft':draft,'trace':[],'emit':noop}
    result=await Agent(store,FakeProvider(settings,draft=draft)).verify(state)
    assert bool(result['verification'].supported_claim_indexes)==(timing in {'before_expiry','operative_transition'})
    if timing in {'after_expiry','unrelated_transition'}:
        assert any('hết hiệu lực' in issue for issue in result['verification'].issues)


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['agentic'])
async def test_clinical_request_stops_without_provider_or_retrieval(store,settings,mode):
    release(store);sid,_=session(store)
    provider=FakeProvider(settings,failure=ProviderUnavailable('Must not be called'))
    async def emit(event):pass
    result=await Agent(store,provider).run(ChatRequest(session_id=sid,message='Tư vấn phác đồ điều trị viêm phổi và liều kháng sinh.',mode=mode),emit)
    assert result.status=='insufficient_evidence'
    assert result.llm_calls==0 and result.tool_calls==0 and result.embedding_calls==0
    assert not result.verified_claims and not result.citations and 'ngoài phạm vi' in result.content


@pytest.mark.asyncio
async def test_hospital_land_planning_stays_in_scope(store,settings):
    release(store);sid,_=session(store)
    async def emit(event):pass
    result=await Agent(store,FakeProvider(settings)).run(ChatRequest(session_id=sid,message='Quy hoạch bệnh viện có đồng nghĩa đã quyết định thu hồi đất không?',mode='agentic'),emit)
    assert result.tool_calls>0 and 'ngoài phạm vi' not in result.content


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['agentic'])
async def test_freshness_question_uses_metadata_and_does_not_fabricate_law(store,settings,mode):
    release(store);sid,_=session(store)
    async def emit(event):pass
    result=await Agent(store,FakeProvider(settings,failure=ProviderUnavailable('Must not be called'))).run(
        ChatRequest(session_id=sid,message='Nếu dữ liệu chatbot nhiều ngày chưa kiểm tra nguồn, có thể bảo đảm quy định hiện nay không?',mode=mode),emit)
    assert result.status=='insufficient_evidence' and result.llm_calls==0
    assert 'Không thể bảo đảm' in result.content and 'mốc kiểm tra' in result.content
    assert not result.citations and not result.verified_claims
    assert 'ngoài phạm vi' not in result.content


@pytest.mark.asyncio
@pytest.mark.parametrize('mode',['agentic'])
async def test_unknown_old_county_needs_finer_location_not_guessed_new_commune(store,settings,mode):
    release(store);sid,_=session(store)
    async def emit(event):pass
    result=await Agent(store,FakeProvider(settings,failure=ProviderUnavailable('Must not be called'))).run(
        ChatRequest(session_id=sid,message='Hồ sơ chỉ ghi huyện Tân Phú cũ, có thể tự đổi thành xã Tân Phú mới và xác định đất thuộc dự án không?',mode=mode),emit)
    assert result.status=='clarification_needed' and result.llm_calls==0
    assert any(t.tool=='normalize_place' for t in result.trace)
    assert 'Tên xã/phường' in result.content and 'chưa đủ' in result.content
    assert not result.citations and not result.verified_claims


@pytest.mark.asyncio
async def test_planning_task_news_only_describes_source_limits_with_literal_proof(store,settings):
    from landlaw.models import Evidence
    from landlaw.agent import State
    text='Cổng thông tin công bố Quyết định 1234/QĐ-UBND phê duyệt Nhiệm vụ quy hoạch phân khu đô thị, tỷ lệ 1/2000.'
    news=document('news',text=text).model_copy(update={'source_kind':'official_news'})
    payload=release(store,[news]);sid,_=session(store)
    async def emit(event):pass
    agent=Agent(store,FakeProvider(settings,failure=ProviderUnavailable('Must not be called')))
    state=State(request=ChatRequest(session_id=sid,message='Bài về 1234/QĐ-UBND phê duyệt nhiệm vụ quy hoạch có đồng nghĩa toàn bộ đồ án và thu hồi từng hộ đã được phê duyệt?'),
        plan=Plan(),release=payload,evidence=[Evidence(document=news,chunk=news.chunks[0],applicability='context')],history=[],as_of=date(2026,10,14),budget=Budget(),trace=[],emit=emit)
    await agent.synthesize(state);await agent.verify(state)
    assert state['draft'].claims[0].kind=='context'
    assert state['verification'].supported_claim_indexes==[0]
    assert state['verification'].supporting_quotes[0].quote in text
    assert 'chưa đủ' in state['draft'].claims[0].text and state['budget'].llm_calls==0
    state['request']=state['request'].model_copy(update={'message':'Bài về 9876/QĐ-UBND phê duyệt nhiệm vụ quy hoạch có đồng nghĩa toàn bộ đồ án đã phê duyệt?'})
    assert agent.planning_task_news(state) is None
    state['request']=state['request'].model_copy(update={'message':'Bài phê duyệt nhiệm vụ quy hoạch có đồng nghĩa toàn bộ đồ án đã phê duyệt?'})
    news.source_kind='project_decision'
    assert agent.planning_task_news(state) is None


@pytest.mark.parametrize('prefix',['dự kiến','chưa','đề xuất','đang xin'])
def test_proposed_or_unapproved_planning_task_never_becomes_approved_fact(prefix):
    from landlaw.models import Evidence
    news=document('news',text=f'Cơ quan {prefix} phê duyệt Nhiệm vụ quy hoạch phân khu đô thị.').model_copy(update={'source_kind':'official_news'})
    state={'request':ChatRequest(session_id='00000000-0000-0000-0000-000000000000',message='Bài phê duyệt nhiệm vụ quy hoạch có đồng nghĩa toàn bộ đồ án đã phê duyệt?'),
           'evidence':[Evidence(document=news,chunk=news.chunks[0],applicability='context')]}
    assert Agent.planning_task_news(state) is None


def test_unrelated_source_gaps_never_replace_verified_evidence_in_prompt():
    from landlaw.models import Evidence
    law=document()
    state={'request':ChatRequest(session_id='00000000-0000-0000-0000-000000000000',message='Điều kiện bồi thường?'),
       'evidence':[Evidence(document=law,chunk=law.chunks[0])],
       'release':{'coverage_gaps':[{'document_id':'missing-price','document_number':'30/2019/QĐ-UBND'}],
                  'unresolved_relations':[]}}
    assert Agent.relevant_gaps(state)==[]
    state['request']=state['request'].model_copy(update={'message':'Theo 30/2019/QĐ-UBND, mức giá là gì?'})
    assert Agent.relevant_gaps(state)[0]['document_id']=='missing-price'
    state['request']=state['request'].model_copy(update={'message':'Điều kiện bồi thường?'})
    state['release']['unresolved_relations']=[{'source_id':'missing-price','target_id':'law','type':'amends'}]
    assert Agent.relevant_gaps(state)[0]['document_id']=='missing-price'
    assert len(Agent.relevant_unresolved(state))==1


@pytest.mark.parametrize('basis,scope,expected',[
    ('Theo khoản 1 Điều 19, các đối tượng được xét hỗ trợ.',['Khoản 3 Điều 19'],False),
    ('Theo khoản 3 Điều 19, mức hỗ trợ được xác định.',['Khoản 3 Điều 19'],True),
    ('Theo khoản 1 Điều 19, các đối tượng được xét hỗ trợ.',['Điều 19'],True),
    ('Các trường hợp tại khoản 1 được hỗ trợ khi có giấy tờ.',['Khoản 3 Điều 19'],True)])
def test_partial_amendment_never_invalidates_proven_different_clause(basis,scope,expected):
    from landlaw.agent import amendment_affects_claim
    from landlaw.models import Evidence,Claim
    law=document();item=Evidence(document=law,chunk=law.chunks[0].model_copy(update={'locator':'Điều 19'}))
    relation={'target_locators_complete':True,'target_locators':scope}
    assert amendment_affects_claim(relation,item,Claim(text=basis,citation_ids=[item.chunk.id])) is expected
    relation['target_locators_complete']=False
    assert amendment_affects_claim(relation,item,Claim(text=basis,citation_ids=[item.chunk.id]))


@pytest.mark.parametrize('project,question', [('songhong','Thông tin dự án sông Hồng?'),('olympic','Đất Olympic được bồi thường không?'),(None,'Quy hoạch sông Hồng đã phê duyệt chưa?')])
async def test_other_projects_are_explicitly_outside_mvp_without_model_calls(store,settings,project,question):
    release(store);sid,_=session(store)
    result=await Agent(store,FakeProvider(settings)).run(ChatRequest(session_id=sid,message=question,project=None),noop)
    assert result.status=='insufficient_evidence'
    assert 'chỉ hỗ trợ Vành đai 4' in result.content
    assert result.llm_calls==0 and not result.citations


async def test_clause_examples_cannot_be_moved_to_a_different_clause_even_if_model_approves(store, settings):
    source = ('Điều 12. Điều kiện hỗ trợ. '
              '1. Đối tượng gồm: a) Cộng đồng dân cư có công trình tín ngưỡng; b) Tổ chức tôn giáo hợp pháp. '
              '2. Các trường hợp quy định tại khoản 1 Điều này được hỗ trợ khi có một trong các điều kiện sau đây: '
              'a) Có giấy xác nhận; b) Có quyết định của cơ quan có thẩm quyền.')
    doc = document(text=source)
    doc.chunks[0].locator = 'Điều 12'
    release(store, [doc]); sid, _ = session(store)
    text = ('Các trường hợp phải thuộc đối tượng khoản 1 Điều này. '
            'Điều kiện tại khoản 2 Điều 12, ví dụ cộng đồng dân cư có công trình tín ngưỡng.')
    draft = Draft(status='answered', claims=[Claim(text=text, citation_ids=['law-1'])])
    result = await Agent(store, FakeProvider(settings, draft=draft)).run(
        ChatRequest(session_id=sid, message='Quy định về các điều kiện hỗ trợ theo Điều 12?'), noop)
    assert result.status == 'insufficient_evidence'
    assert not result.verified_claims
    assert draft.claims[0].text == text


async def test_semantic_issue_blocks_a_contradictorily_approved_claim(store, settings):
    release(store); sid, _ = session(store)
    verification = Verification(supported_claim_indexes=[0], issues=['Claim 0: chủ thể không được nguồn chứng minh'])
    result = await Agent(store, FakeProvider(settings, verification=verification)).run(
        ChatRequest(session_id=sid, message='Điều kiện bồi thường được quy định thế nào?'), noop)
    assert result.status == 'insufficient_evidence'
    assert not result.verified_claims and not result.citations


@pytest.mark.parametrize('verification', [
    Verification(supported_claim_indexes=[0], issues=['Chủ thể và điều kiện chưa được chứng minh']),
    Verification(supported_claim_indexes=[0], needs_more_evidence=True, followup_query='điều kiện bồi thường'),
])
async def test_unresolved_verification_blocks_release_even_when_all_indexes_are_approved(store, settings, verification):
    release(store); sid, _ = session(store)
    provider = FakeProvider(settings, verification=verification)
    provider.draft.next_steps = ['Đối chiếu hồ sơ đã ẩn danh.']
    result = await Agent(store, provider).run(
        ChatRequest(session_id=sid, message='Điều kiện bồi thường được quy định thế nào?'), noop)
    assert result.status == 'insufficient_evidence'
    assert not result.verified_claims and not result.citations
    assert provider.draft.claims[0].text not in result.content
    assert provider.draft.next_steps[0] not in result.content
    assert result.llm_calls <= 6 and result.tool_calls <= 12


@pytest.mark.parametrize('needs_more_evidence', [False, True])
async def test_resolved_verification_can_publish_after_repair_or_retrieval(store, settings, needs_more_evidence):
    release(store); sid, _ = session(store)

    class RecoveringProvider(FakeProvider):
        checks = 0

        async def generate(self, schema, instruction, payload, budget):
            if schema is Verification:
                self.checks += 1
                self.verification = (Verification(supported_claim_indexes=[0],
                    issues=[] if needs_more_evidence else ['Cần kiểm tra lại điều kiện'],
                    needs_more_evidence=needs_more_evidence, followup_query='điều kiện bồi thường')
                    if self.checks == 1 else Verification(supported_claim_indexes=[0]))
            return await super().generate(schema, instruction, payload, budget)

    provider = RecoveringProvider(settings)
    result = await Agent(store, provider).run(
        ChatRequest(session_id=sid, message='Điều kiện bồi thường được quy định thế nào?'), noop)
    assert provider.checks == 2
    assert result.status == 'answered' and result.verified_claims and result.citations
    assert result.llm_calls <= 6 and result.tool_calls <= 12
    assert any(event.step == 'repair' for event in result.trace) is not needs_more_evidence


@pytest.mark.parametrize('qualified', [False, True])
async def test_future_qualification_must_be_verified_before_finish(store, settings, qualified):
    start = date(2027, 1, 1)
    law = document(document_number='40/2027/QĐ-UBND',
                   text='Điều 1. Quyết định có hiệu lực thi hành từ ngày 01/01/2027.')
    law.effective_from = start
    release(store, [law]); sid, _ = session(store)
    text = 'Quyết định có hiệu lực thi hành từ ngày 01/01/2027.'
    if qualified:
        text += ' Văn bản này chưa có hiệu lực tại ngày 18/10/2026.'
    draft = Draft(status='answered', claims=[Claim(kind='applicability', text=text, citation_ids=['law-1'])])
    result = await Agent(store, FakeProvider(settings, draft=draft)).run(
        ChatRequest(session_id=sid, message='40/2027/QĐ-UBND có hiệu lực từ khi nào?', as_of=date(2026, 10, 18)), noop)
    if qualified:
        assert result.status == 'answered', result.trace
        assert result.verified_claims[0].text == text
    else:
        assert result.status == 'insufficient_evidence'
        assert not result.verified_claims and not result.citations
    assert draft.claims[0].text == text


async def test_private_guarantee_requests_clarification_without_consuming_tools(store, settings):
    release(store); sid, _ = session(store)
    result = await Agent(store, FakeProvider(settings)).run(
        ChatRequest(session_id=sid, message='Nhà tôi bị thu hồi thì chắc chắn được tái định cư đúng không?'), noop)
    assert result.status == 'clarification_needed'
    assert result.llm_calls == result.tool_calls == 0


async def test_alternative_documents_cannot_become_cumulative_requirements(store, settings):
    source = ('Điều 12. Điều kiện. 2. Các trường hợp quy định tại khoản 1 Điều này được hỗ trợ '
              'khi có một trong các điều kiện sau đây: a) Có giấy chứng nhận; b) Có quyết định giao đất.')
    doc = document(text=source); doc.chunks[0].locator = 'Điều 12'
    release(store, [doc]); sid, _ = session(store)
    text = ('Đối tượng phải thuộc khoản 1 Điều này. Ngoài giấy chứng nhận, người được hỗ trợ '
            'còn phải có quyết định giao đất theo khoản 2 Điều 12.')
    draft = Draft(status='answered', claims=[Claim(text=text, citation_ids=['law-1'])])
    result = await Agent(store, FakeProvider(settings, draft=draft)).run(
        ChatRequest(session_id=sid, message='Giấy chứng nhận có phải điều kiện duy nhất để được hỗ trợ?'), noop)
    assert result.status == 'insufficient_evidence'
    assert not result.verified_claims


async def test_planner_keeps_relevant_sources_beyond_catalogue_prefix_with_bounded_context(store, settings, monkeypatch):
    import json
    docs = [document(f'doc-{i}') for i in range(60)]
    for doc in docs:
        doc.title = 'Văn bản về các điều kiện theo nguồn chính thức. ' * 15
    payload = release(store, docs)
    monkeypatch.setattr(store, 'article_candidates', lambda *_: [
        {'document_id': 'doc-59', 'locator': f'Điều {i}', 'heading': 'Quy định hỗ trợ từ nguồn.'}
        for i in range(1, 41)])
    class InspectPlanner(FakeProvider):
        async def generate(self, schema, instruction, context, budget):
            assert schema is Plan
            assert len(json.dumps(context, ensure_ascii=False)) < 6000
            assert any(row[0] == 'doc-59' for row in context['catalogue'])
            assert all(row[0] != 'doc-0' for row in context['catalogue'])
            return Plan(tools=[ToolCall(name='search_law', query='các loại hỗ trợ')])
    sid, _ = session(store)
    state = {'request': ChatRequest(session_id=sid, message='Khi thu hồi đất có những loại hỗ trợ nào?'),
             'release': payload, 'as_of': date(2024, 8, 2), 'history': [], 'evidence': [],
             'budget': Budget(), 'trace': [], 'emit': noop}
    result = await Agent(store, InspectPlanner(settings)).plan(state)
    assert result['plan'].tools[0].name == 'search_law'


async def test_assistance_catalogue_is_published_as_verified_without_extra_conditions(store, settings):
    source = ('Điều 108. Hỗ trợ khi Nhà nước thu hồi đất. '
              '1. Hỗ trợ gồm: a) Hỗ trợ ổn định đời sống; b) Hỗ trợ ổn định sản xuất, kinh doanh.')
    release(store,[document(text=source)]);sid,_=session(store)
    draft=Draft(status='answered',claims=[Claim(text='Theo Điều 108, Nhà nước hỗ trợ gồm hỗ trợ ổn định đời sống và hỗ trợ ổn định sản xuất, kinh doanh.',citation_ids=['law-1'])])
    result=await Agent(store,FakeProvider(settings,draft=draft)).run(ChatRequest(session_id=sid,message='Các nhóm hỗ trợ là gì?',as_of=date(2024,8,2)),noop)
    assert result.status=='answered'
    assert draft.claims[0].text in result.content
    assert 'chưa phải kết luận hộ cụ thể được nhận tất cả' not in result.content
    assert 'Đây là danh mục' not in result.content


@pytest.mark.parametrize('text',[
    'Khi chưa được bố trí chỗ ở mới, hộ gia đình đủ điều kiện được hỗ trợ tái định cư và được nhận tiền để tự lo chỗ ở.',
    'Nếu đã phê duyệt dự toán chi phí bảo đảm và cưỡng chế thu hồi đất, các chi phí bồi thường, hỗ trợ, tái định cư tiếp tục theo quy định cũ.'
])
async def test_new_trigger_and_implementation_costs_cannot_become_household_entitlements(store,settings,text):
    source=('Điều 12. Trường hợp hộ gia đình đủ điều kiện hỗ trợ tái định cư mà có nhu cầu tự lo chỗ ở thì được nhận tiền hỗ trợ. '
            'Dự toán chi phí bảo đảm cho việc tổ chức thực hiện bồi thường, hỗ trợ, tái định cư và chi phí cưỡng chế đã phê duyệt thì tiếp tục lập, sử dụng và thanh, quyết toán kinh phí tổ chức theo quy định cũ.')
    release(store,[document(text=source)]);sid,_=session(store)
    result=await Agent(store,FakeProvider(settings,draft=Draft(status='answered',claims=[Claim(text=text,citation_ids=['law-1'])]))).run(ChatRequest(session_id=sid,message='Thủ tục thu hồi đất và tái định cư cần bảo đảm gì?',as_of=date(2024,8,2)),noop)
    assert result.status=='insufficient_evidence' and not result.verified_claims


async def test_unknown_number_is_missing_evidence_without_presupposing_a_fabricated_law(store,settings):
    release(store);sid,_=session(store)
    result=await Agent(store,FakeProvider(settings)).run(ChatRequest(session_id=sid,message='Nghị định 987654/2026/NĐ-CP cho mọi hộ nhận tiền hỗ trợ đúng không?'),noop)
    assert result.status=='insufficient_evidence' and result.llm_calls==result.tool_calls==0
    assert 'Chưa có văn bản' in result.content and 'Thông tin cần bổ sung' not in result.content


async def test_client_history_and_old_citations_are_context_not_evidence(store,settings):
    release(store);sid,_=session(store);histories=[]
    class Recording(FakeProvider):
        async def generate(self,schema,instruction,payload,budget):
            histories.append(payload.get('history',[]))
            return await super().generate(schema,instruction,payload,budget)
    draft=Draft(status='answered',claims=[Claim(text='Mọi hộ được nhận số tiền được nói trong lịch sử.',citation_ids=['invented-chunk'])])
    result=await Agent(store,Recording(settings,draft=draft)).run(ChatRequest(session_id=sid,message='Điều kiện hỗ trợ có được nguồn chứng minh không?',
        history=[{'role':'user','content':'Câu trước về hỗ trợ.'},{'role':'assistant','content':'Lời đáp cũ không phải chứng cứ.',
          'citations':[{'document_id':'invented-law','document_number':'987654/2026','locator':'Điều 1'}]}]),noop)
    assert result.status=='insufficient_evidence' and not result.citations
    assert all(not h[1]['citations'] for h in histories if len(h)==2)
    assert all('invented-chunk' not in x.document_ids for x in result.trace)


@pytest.mark.parametrize('claim',[
 'Hộ gia đình được hỗ trợ bằng tiền không quá 05 lần giá đất.',
 'Hộ gia đình nhận giao khoán có nguồn thu nhập ổn định cũng được hỗ trợ chuyển nghề.'
])
async def test_price_multiple_keeps_valuation_basis_and_contracted_land_exception(store,settings,claim):
    source=('Điều 12. Hỗ trợ không quá 05 lần giá đất nông nghiệp cùng loại trong bảng giá đất, không vượt quá hạn mức giao đất. '
            'Hộ gia đình nhận giao khoán của nông trường có nguồn thu nhập ổn định được xét hỗ trợ, trừ trường hợp cá nhân đã nghỉ hưu hoặc thôi việc được hưởng trợ cấp.')
    release(store,[document(text=source)]);sid,_=session(store)
    result=await Agent(store,FakeProvider(settings,draft=Draft(status='answered',claims=[Claim(text=claim,citation_ids=['law-1'])]))).run(ChatRequest(session_id=sid,message='Điều kiện hỗ trợ được quy định thế nào?',as_of=date(2024,8,2)),noop)
    assert result.status=='insufficient_evidence' and not result.verified_claims


def test_image_page_citation_uses_exact_original_image_not_a_composite_pdf():
    from landlaw.agent import citation_source_url
    from landlaw.models import Evidence, SourcePage
    doc = document(source_pages=[SourcePage(page_index=2,
        url='https://xdcs.cdnchinhphu.vn/original-page-3.jpg', checksum='a'*64)])
    chunk = doc.chunks[0].model_copy(update={'id':'law-2-0-0','page':3})
    assert citation_source_url(Evidence(document=doc,chunk=chunk)) == 'https://xdcs.cdnchinhphu.vn/original-page-3.jpg'
    assert citation_source_url(Evidence(document=doc,chunk=chunk.model_copy(update={'id':'law-1-0-0','page':2}))) is None


@pytest.mark.parametrize('text,approved', [
    ('Khi Nhà nước thu hồi đất, Nhà nước phải thực hiện hỗ trợ ổn định đời sống, hỗ trợ sản xuất, hỗ trợ tái định cư.', False),
    ('Pháp luật quy định ba loại hỗ trợ chính: hỗ trợ ổn định đời sống, hỗ trợ sản xuất, hỗ trợ tái định cư.', False),
    ('Để nhận hỗ trợ, hộ phải có hợp đồng giao khoán theo quy định.', False),
    ('Ví dụ ba loại hỗ trợ trong danh mục: hỗ trợ ổn định đời sống, hỗ trợ ổn định sản xuất, hỗ trợ tái định cư.', True),
    ('Danh mục gồm sáu loại hỗ trợ: hỗ trợ ổn định đời sống, hỗ trợ ổn định sản xuất, hỗ trợ di dời vật nuôi, hỗ trợ chuyển nghề, hỗ trợ tái định cư, hỗ trợ tháo dỡ.', True),
])
async def test_assistance_catalogue_cannot_be_repaired_by_a_post_verification_disclaimer(store, settings, text, approved):
    from landlaw.models import Evidence
    source = ('Điều 1. Các khoản hỗ trợ khi Nhà nước thu hồi đất bao gồm: '
              'a) Hỗ trợ ổn định đời sống; b) Hỗ trợ ổn định sản xuất; c) Hỗ trợ di dời vật nuôi; '
              'd) Hỗ trợ chuyển nghề; đ) Hỗ trợ tái định cư; e) Hỗ trợ tháo dỡ. '
              'Người nhận giao khoán đất nông nghiệp phải có hợp đồng giao khoán nếu thuộc nhóm được quy định riêng.')
    doc = document(text=source)
    payload = release(store, [doc])
    draft = Draft(status='answered', claims=[Claim(text=text, citation_ids=['law-1'])])
    state = {'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000', message='Có những nhóm hỗ trợ nào?'),
             'budget':Budget(), 'release':payload, 'as_of':date(2024,8,2), 'plan':Plan(),
             'evidence':[Evidence(chunk=doc.chunks[0], document=doc, applicability='current')],
             'draft':draft, 'trace':[], 'emit':noop}
    agent = Agent(store, FakeProvider(settings, draft=draft))
    supplied_synthesis_fixture(state)
    await agent.verify(state)
    assert bool(state['verification'].supported_claim_indexes) == approved
    await agent.finish(state)
    assert bool(state['result'].verified_claims) == approved
    assert 'Đây là danh mục loại hỗ trợ trong nguồn' not in state['result'].content
    assert 'Chưa giải thích điều kiện riêng' not in state['result'].content


@pytest.mark.parametrize('qualified', [False, True])
async def test_farming_actor_cannot_lose_income_and_approval_date_conditions(store,settings,qualified):
    from landlaw.models import Evidence
    source=('Điều 12. Hỗ trợ. 1. Cá nhân trực tiếp sản xuất nông nghiệp được hỗ trợ khi '
            'có thu nhập từ sản xuất nông nghiệp trên đất đó tại thời điểm phê duyệt phương án '
            'bồi thường và không thuộc trường hợp người hưởng lương hưu.')
    law=document(text=source);law.chunks[0].locator='Điều 12'
    payload=release(store,[law])
    text='Cá nhân trực tiếp sản xuất nông nghiệp được hỗ trợ'
    text+=(' khi có thu nhập từ sản xuất nông nghiệp trên đất đó tại thời điểm phê duyệt phương án '
           'bồi thường và không thuộc trường hợp người hưởng lương hưu.' if qualified else ' nếu không hưởng lương hưu.')
    state={'request':ChatRequest(session_id='0'*32,message='Ai được hỗ trợ?'),
        'release':payload,
        'draft':Draft(status='answered',claims=[Claim(text=text,citation_ids=['law-1'])]),
        'evidence':[Evidence(chunk=law.chunks[0],document=law,applicability='current')],
        'as_of':date(2024,8,2),'budget':Budget(),'trace':[],'emit':noop,'history':[]}
    supplied_synthesis_fixture(state)
    await Agent(store,FakeProvider(settings)).verify(state)
    assert bool(state['verification'].supported_claim_indexes) is qualified


@pytest.mark.parametrize('independent', [False, True])
async def test_alternative_document_claim_must_carry_its_own_actor_prerequisite(store,settings,independent):
    from landlaw.models import Evidence
    source=('Điều 12. Điều kiện. 2. Các trường hợp quy định tại khoản 1 Điều này được bồi thường '
            'khi có một trong các điều kiện sau: a) Có giấy chứng nhận; b) Có quyết định giao đất.')
    law=document(text=source);law.chunks[0].locator='Điều 12'
    payload=release(store,[law])
    text='Được bồi thường khi có giấy chứng nhận hoặc có quyết định giao đất.'
    if independent:text='Trường hợp thuộc khoản 1 Điều này '+text[0].lower()+text[1:]
    state={'request':ChatRequest(session_id='0'*32,message='Giấy chứng nhận có phải điều kiện duy nhất?'),
        'release':payload,
        'draft':Draft(status='answered',claims=[
            Claim(text='Đối tượng phải thuộc khoản 1 Điều này.',citation_ids=['law-1']),
            Claim(text=text,citation_ids=['law-1'])]),
        'evidence':[Evidence(chunk=law.chunks[0],document=law,applicability='current')],
        'as_of':date(2024,8,2),'budget':Budget(),'trace':[],'emit':noop,'history':[]}
    provider=FakeProvider(settings,verification=Verification(supported_claim_indexes=[0,1]))
    supplied_synthesis_fixture(state)
    await Agent(store,provider).verify(state)
    assert bool(state['verification'].supported_claim_indexes) is independent


def test_ranked_principle_keeps_its_continuation_before_keyword_dense_neighbor(store,settings):
    from landlaw.models import Evidence
    law=document()
    opening=law.chunks[0].model_copy(update={'id':'principle-start','locator':'Điều 12',
        'text':'Điều 12. Nguyên tắc bồi thường, hỗ trợ và tái định cư. '+('Phạm vi và nguyên tắc chung. '*20)})
    continuation=opening.model_copy(update={'id':'principle-end',
        'text':'6. Việc bố trí tái định cư phải hoàn thành trước khi có quyết định thu hồi đất. '+('Điều kiện về nơi ở và cơ quan thực hiện. '*25)})
    neighbor=opening.model_copy(update={'id':'nearby-benefit','locator':'Điều 19',
        'text':'Điều 19. Bố trí chỗ ở mới, hỗ trợ thuê nhà. '+('Bố trí chỗ ở mới và hỗ trợ thuê nhà. '*140)})
    state={'request':ChatRequest(session_id='0'*32,message='Chưa bố trí chỗ ở mới thì thu hồi đất cần bảo đảm gì?'),
        'evidence':[Evidence(chunk=c,document=law,applicability='current') for c in [opening,neighbor,continuation]],
        'release':{'documents':[law.model_dump(mode='json')],'relations':[]}}
    passages,_=Agent(store,FakeProvider(settings)).prompt_context(state)
    assert 'principle-end' in {p['citation_id'] for p in passages}
    assert {p['citation_id'] for p in passages[:2]}=={'principle-start','principle-end'}


def test_topic_evidence_cannot_be_displaced_by_generic_authority_headings(store,settings):
    from landlaw.models import Evidence
    law=document()
    generic=law.chunks[0].model_copy(update={'id':'general-authority','locator':'Điều 4',
        'text':'Điều 4. Cơ quan có thẩm quyền quy định. '+('Ủy ban nhân dân có thẩm quyền theo quy định của pháp luật. '*60)})
    precise=generic.model_copy(update={'id':'asset-rule','locator':'Điều 16',
        'text':'Điều 16. Bồi thường chi phí di chuyển tài sản. 1. Bồi thường chi phí di chuyển tài sản khi thu hồi đất. 2. Ủy ban nhân dân cấp tỉnh quy định mức bồi thường.'})
    state={'request':ChatRequest(session_id='0'*32,message='Ai có thẩm quyền quy định mức bồi thường chi phí chuyển tài sản?'),
        'evidence':[Evidence(chunk=c,document=law,applicability='current') for c in [generic,precise]],
        'release':{'documents':[law.model_dump(mode='json')],'relations':[]}}
    passages,_=Agent(store,FakeProvider(settings)).prompt_context(state)
    assert passages[0]['citation_id']=='asset-rule'


def test_model_list_formatting_changes_only_whitespace_not_dates_or_decimals():
    from landlaw.agent import model_passage_text
    text='Điều 12. Nội dung. 1. Mốc 02/04/2026, hệ số 1.5; a) Trường hợp thứ nhất; b) Trường hợp thứ hai. 2. Điều kiện tiếp theo.'
    formatted=model_passage_text(text)
    assert ' '.join(formatted.split())==' '.join(text.split())
    assert '\n1. ' in formatted and '\na) ' in formatted and '\n2. ' in formatted
    assert '02/04/2026' in formatted and '1.5' in formatted


async def test_repair_receives_the_rejected_draft_with_matching_claim_indexes_and_aliases(store, settings):
    source = ('Điều 91. Việc phê duyệt phương án bồi thường, hỗ trợ, tái định cư và '
              'việc bố trí tái định cư phải được hoàn thành trước khi có quyết định thu hồi đất.')
    release(store, [document(text=source)])
    sid, _ = session(store)
    valid = Claim(text=source.split('. ', 1)[1], citation_ids=['law-1'])
    invalid = Claim(text='Nếu chưa có nhà mới, mọi hộ được nhận đất ở.', citation_ids=['law-1'])

    class RepairProvider(FakeProvider):
        def __init__(self, settings):
            super().__init__(settings)
            self.drafts = 0

        async def generate(self, schema, instruction, payload, budget):
            if schema is Draft:
                budget.llm()
                self.drafts += 1
                if self.drafts == 1:
                    assert payload.get('previous_draft') is None
                    return Draft(status='answered', claims=[valid, invalid])
                previous = payload['previous_draft']
                assert [c['text'] for c in previous['claims']] == [valid.text, invalid.text]
                assert all(c['citation_ids'] == ['C1'] for c in previous['claims'])
                assert any(issue.startswith('Claim 1:') for issue in payload['previous_issues'])
                assert 'verified again' in instruction
                return Draft(status='answered', claims=[valid])
            return await super().generate(schema, instruction, payload, budget)

    provider = RepairProvider(settings)
    result = await Agent(store, provider).run(ChatRequest(session_id=sid,
        message='Việc thu hồi đất và bố trí tái định cư cần bảo đảm gì?'), noop)
    assert provider.drafts == 2 and result.llm_calls == 3
    assert result.status == 'answered' and result.verified_claims == [valid]
    assert invalid.text not in result.content
    assert any(event.step == 'verification' for event in result.trace)


@pytest.mark.parametrize('qualified', [False, True])
async def test_contract_land_support_cannot_omit_the_sources_contract_requirement(store, settings, qualified):
    from landlaw.models import Evidence
    source = ('Điều 19. Hộ gia đình, cá nhân sử dụng đất do nhận giao khoán đất để sử dụng vào mục đích '
              'nông nghiệp từ các nông, lâm trường quốc doanh và có hợp đồng giao khoán sử dụng đất '
              'thì Ủy ban nhân dân cấp tỉnh quyết định mức hỗ trợ, thời gian hỗ trợ.')
    doc = document(text=source)
    payload = release(store, [doc])
    text = ('Hộ gia đình, cá nhân nhận giao khoán đất nông nghiệp từ các nông, lâm trường quốc doanh '
            + ('và có hợp đồng giao khoán sử dụng đất ' if qualified else '')
            + 'thì Ủy ban nhân dân cấp tỉnh quyết định mức hỗ trợ, thời gian hỗ trợ.')
    draft = Draft(status='answered', claims=[Claim(text=text, citation_ids=['law-1'])])
    state = {'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000', message='Hỗ trợ phụ thuộc điều kiện gì?'),
             'budget':Budget(), 'release':payload, 'as_of':date(2024,8,2), 'plan':Plan(),
             'evidence':[Evidence(chunk=doc.chunks[0], document=doc, applicability='current')],
             'draft':draft, 'trace':[], 'emit':noop}
    agent = Agent(store, FakeProvider(settings))
    supplied_synthesis_fixture(state)
    await agent.verify(state)
    await agent.finish(state)
    assert bool(state['result'].verified_claims) is qualified
    if not qualified:
        assert not state['result'].citations
        assert 'và có hợp đồng' not in state['result'].content


@pytest.mark.parametrize('independent', [False, True])
async def test_legal_rule_reference_to_another_claim_is_not_independent_proof(store, settings, independent):
    from landlaw.models import Evidence
    doc = document(document_number='88/2024/NĐ-CP', text='Hộ gia đình đủ điều kiện được bồi thường về đất được xem xét hỗ trợ.')
    commencement = doc.chunks[0].model_copy(update={'id':'law-2', 'locator':'Điều 30',
        'text':'Nghị định này có hiệu lực thi hành từ ngày 01 tháng 8 năm 2024.'})
    doc.chunks.append(commencement)
    payload = release(store, [doc])
    text = ('Nghị định này có hiệu lực thi hành từ ngày 01/08/2024.' if independent else
            'Các quy định trên áp dụng cho mọi hồ sơ kể từ ngày 01/08/2024.')
    draft = Draft(status='answered', claims=[Claim(text=doc.chunks[0].text, citation_ids=['law-1']),
        Claim(kind='applicability' if independent else 'legal_rule', text=text, citation_ids=['law-2'])])
    state = {'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000', message='Nguồn quy định hỗ trợ thế nào?'),
             'budget':Budget(), 'release':payload, 'as_of':date(2024,8,2), 'plan':Plan(),
             'evidence':[Evidence(chunk=c, document=doc, applicability='current') for c in doc.chunks],
             'draft':draft, 'trace':[], 'emit':noop}
    agent = Agent(store, FakeProvider(settings, verification=Verification(supported_claim_indexes=[0,1])))
    supplied_synthesis_fixture(state)
    await agent.verify(state)
    await agent.finish(state)
    assert bool(state['result'].verified_claims) is independent
    if not independent:
        assert not state['result'].citations and text not in state['result'].content


@pytest.mark.parametrize('broader_actor', [False, True])
async def test_state_enterprise_cannot_replace_the_specific_contract_land_source_actor(store, settings, broader_actor):
    from landlaw.models import Evidence
    source = ('Điều 19. Hộ gia đình, cá nhân nhận giao khoán đất nông nghiệp từ các nông, lâm trường quốc doanh '
              'và có hợp đồng giao khoán sử dụng đất thì Ủy ban nhân dân cấp tỉnh quyết định mức hỗ trợ.')
    doc = document(text=source)
    payload = release(store, [doc])
    actor = 'doanh nghiệp nhà nước' if broader_actor else 'các nông, lâm trường quốc doanh'
    text = ('Hộ gia đình, cá nhân nhận giao khoán đất nông nghiệp từ '+actor+
            ' và có hợp đồng giao khoán sử dụng đất thì Ủy ban nhân dân cấp tỉnh quyết định mức hỗ trợ.')
    draft = Draft(status='answered', claims=[Claim(text=text, citation_ids=['law-1'])])
    state = {'request':ChatRequest(session_id='00000000-0000-4000-8000-000000000000', message='Nhóm nhận giao khoán nào được xem xét hỗ trợ?'),
             'budget':Budget(), 'release':payload, 'as_of':date(2024,8,2), 'plan':Plan(),
             'evidence':[Evidence(chunk=doc.chunks[0], document=doc, applicability='current')],
             'draft':draft, 'trace':[], 'emit':noop}
    agent = Agent(store, FakeProvider(settings))
    supplied_synthesis_fixture(state)
    await agent.verify(state)
    await agent.finish(state)
    assert bool(state['result'].verified_claims) is not broader_actor


def test_order_question_prioritizes_operating_prerequisite_over_article_heading(store,settings):
    from landlaw.models import Evidence
    law=document(document_number='31/2024/QH15')
    heading=law.chunks[0].model_copy(update={'id':'law-heading','locator':'Điều 91',
        'text':'Điều 91. Nguyên tắc bồi thường, hỗ trợ, tái định cư khi Nhà nước thu hồi đất. 1. Việc bồi thường phải bảo đảm dân chủ, công khai, minh bạch.'})
    operative=law.chunks[0].model_copy(update={'id':'law-prerequisite','locator':'Điều 91 · ngữ cảnh',
        'text':'6. Việc phê duyệt phương án bồi thường, hỗ trợ, tái định cư và việc bố trí tái định cư phải được hoàn thành trước khi có quyết định thu hồi đất.'})
    law.chunks=[heading,operative]
    state={'request':ChatRequest(session_id='00000000-0000-0000-0000-000000000000',
        message='Chưa được bố trí chỗ ở mới thì thu hồi đất ở cần bảo đảm gì?'),
        'evidence':[Evidence(document=law,chunk=c) for c in law.chunks],
        'release':{'documents':[law.model_dump(mode='json')],'relations':[]}}
    passages,_=Agent(store,FakeProvider(settings)).prompt_context(state)
    assert passages[0]['citation_id']=='law-prerequisite'
    assert {p['citation_id'] for p in passages}=={'law-heading','law-prerequisite'}
