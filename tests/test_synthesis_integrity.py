"""Synthesis input and citation-boundary regressions; no external model calls."""
import json
from datetime import date

import pytest

from conftest import document, release
from test_agent import FakeProvider, noop
from test_source_review_policy import approved_state
from landlaw.agent import Agent, Verification, SupportingQuote, model_passage_text, source_clause_spans, synthesis_passages, quote_matches
from landlaw.models import ChatRequest, Claim, Draft, Evidence
from landlaw.security import digest
from landlaw.synthesis_context import pack_context, paragraph_view


def context_item(doc, chunk=None):
    chunk=chunk or doc.chunks[0]
    return {'citation_id':chunk.id,'document_id':doc.id,'text':chunk.text,'locator':chunk.locator,
        'page':chunk.page,'applicability':'current','document_number':doc.document_number,
        'title':doc.title,'kind':doc.source_kind,'effective_from':str(doc.effective_from),
        'effective_to':None,'provision_validity':[],'source_review_notes':'','legal_relations':[]}


def pack(items, question='điều kiện hỗ trợ'):
    return pack_context(items,question,synthesis_passages,model_passage_text,source_clause_spans,date(2026,10,21))


def wire_size(passages, docs):
    shown=synthesis_passages([{**p,'citation_id':f'C{i+1}'} for i,p in enumerate(passages)])
    return len(json.dumps([shown,docs],ensure_ascii=False,separators=(',',':')))


@pytest.mark.parametrize('kind',['amends','repeals','overrides'])
def test_effective_dependency_precedes_repeated_similarity_hits(kind):
    base=context_item(document('original',text='Điều 1. Điều kiện hỗ trợ khi thu hồi đất. '+('Điều kiện đủ. '*60)))
    modifier=context_item(document('modifier',text='Điều 1. Sửa đổi điều kiện tại Điều 1 văn bản gốc.'))
    modifier['legal_relations']=[{'source_id':'modifier','target_id':'original','type':kind,
        'source_locator':'Điều 1','target_locators':['Điều 1'],'target_locators_complete':True,
        'source_effective_from':'2026-01-01','source_verified':True}]
    repeats=[context_item(document(f'noise-{n}',text='Nội dung tương tự. '*100)) for n in range(8)]
    passages,docs,reasons=pack([base,*repeats,modifier])
    assert modifier['citation_id'] in {p['citation_id'] for p in passages}
    assert wire_size(passages,docs)<=7000
    assert reasons[modifier['citation_id']].startswith('included')


def test_numbered_projection_keeps_condition_and_its_explicit_exception():
    raw=('Điều 8. Hỗ trợ. 1. Việc không liên quan. '
         '2. Hộ cần di chuyển được hỗ trợ, trừ trường hợp tại khoản 3 Điều này. '
         '3. Hộ đã được bố trí chỗ ở không nhận hỗ trợ này. '
         '4. Chủ đầu tư có nghĩa vụ báo cáo.')
    item=context_item(document(text=raw))
    view=paragraph_view(item,'hộ cần di chuyển hỗ trợ',model_passage_text,source_clause_spans,{'2'})
    assert '2. Hộ cần' in view['text'] and '3. Hộ đã' in view['text']
    assert '4. Chủ' not in view['text']
    assert quote_matches(view['text'],raw)


def test_projection_preserves_referenced_actor_group_and_or_conditions():
    raw=('Điều 8. Hỗ trợ. 1. Hộ đang sử dụng đất nông nghiệp hợp pháp. '
         '2. Các trường hợp quy định tại khoản 1 Điều này được hỗ trợ khi có giấy xác nhận hoặc quyết định. '
         '3. Cơ quan báo cáo định kỳ.')
    view=paragraph_view(context_item(document(text=raw)),'giấy xác nhận hoặc quyết định',model_passage_text,source_clause_spans,{'2'})
    assert '1. Hộ đang' in view['text'] and 'hoặc quyết định' in view['text']
    assert quote_matches(view['text'],raw)


def test_quoted_amendment_cross_reference_is_not_bound_to_outer_paragraph():
    raw=('Điều 8. Sửa đổi văn bản khác. 1. Quy định không liên quan. '
         '2. Bổ sung khoản 3 Điều 9 như sau: “3. Hộ quy định tại khoản 1 Điều này được hỗ trợ.”. '
         '3. Cơ quan báo cáo định kỳ.')
    view=paragraph_view(context_item(document(text=raw)),'được hỗ trợ',model_passage_text,source_clause_spans,{'2'})
    assert '1. Quy định không liên quan' not in view['text']
    assert '“3. Hộ quy định tại khoản 1 Điều này được hỗ trợ.”.' in view['text']
    assert quote_matches(view['text'],raw)


def test_no_clipping_of_unstructured_or_incomplete_source():
    item=context_item(document(text='Nội dung công khai chưa được chia khoản '+('phạm vi chưa đầy đủ '*500)))
    passages,docs,reasons=pack([item])
    assert not passages and not docs
    assert reasons[item['citation_id']]=='context_budget'
    assert paragraph_view(item,'phạm vi',model_passage_text,source_clause_spans)==item


def test_projection_does_not_finish_an_incomplete_paragraph():
    raw='Điều 8. Hỗ trợ. 1. Quy định khác. 2. Hộ đủ điều kiện được hỗ trợ khi'
    item=context_item(document(text=raw))
    assert paragraph_view(item,'hộ đủ điều kiện hỗ trợ',model_passage_text,source_clause_spans,{'2'})==item


def test_parent_cannot_replace_child_outside_admitted_scope(store,settings):
    doc=document()
    child=doc.chunks[0];child.parent_id='law-parent'
    parent=child.model_copy(update={'id':'law-parent','parent_id':None,'text':child.text+' Phần chưa review.'})
    parent.checksum=digest(parent.text)
    state={'evidence':[Evidence(document=doc,chunk=c) for c in [child,parent]],
           'admitted_source_ids':{child.id},'release':{'documents':[doc.model_dump(mode='json')],'relations':[]}}
    passages,_=Agent(store,FakeProvider(settings)).prompt_context(state)
    assert [p['citation_id'] for p in passages]==[child.id]
    assert state['synthesis_diagnostics']['selection_reasons'][parent.id]=='not_admitted'


def test_compact_links_do_not_infer_whole_document_amendment():
    first=context_item(document('base',text='Điều 1. Điều kiện. '+('công khai '*500)))
    other=context_item(document('modifier',text='Điều 1. Chỉ sửa điểm b khoản 2 Điều 1.'))
    other['legal_relations']=[{'source_id':'modifier','target_id':'base','type':'amends',
        'source_locator':'Điều 1','target_locators':['Điểm b khoản 2 Điều 1'],'target_locators_complete':True}]
    noise=[context_item(document(f'extra-{i}',text='Dữ liệu tham khảo. '*100)) for i in range(5)]
    passages,docs,_=pack([first,*noise,other])
    assert wire_size(passages,docs)<=7000
    assert any(doc.get('relation_scope')=='source text' for doc in docs)
    assert 'Chỉ sửa điểm b khoản 2 Điều 1.' in next(p['text'] for p in passages if p['document_id']=='modifier')


class AliasProvider(FakeProvider):
    def __init__(self,settings,*,hidden_id=None):
        super().__init__(settings)
        self.hidden_id=hidden_id
        self.payloads=[]
    async def generate(self,schema,instruction,payload,budget):
        if schema is Draft:
            self.payloads.append(payload)
            budget.llm()
            cid=self.hidden_id or payload['allowed_citation_ids'][0]
            return Draft(status='answered',claims=[Claim(text='Điều kiện bồi thường khi thu hồi đất phải được kiểm tra theo hồ sơ.',citation_ids=[cid])])
        return await super().generate(schema,instruction,payload,budget)


async def test_valid_alias_citation_has_actual_exposure_and_verifier_proof(store,settings):
    release(store)
    provider=AliasProvider(settings)
    result=await Agent(store,provider).run(ChatRequest(session_id='0'*36,message='Điều kiện bồi thường?'),noop)
    assert result.status=='answered' and [c.id for c in result.citations]==['law-1']
    assert provider.payloads[0]['evidence'][0]['citation_id']=='C1'


@pytest.mark.parametrize('admitted',[True,False])
async def test_retrieved_only_source_cannot_publish_with_approving_judge(store,settings,admitted):
    doc=document()
    hidden=doc.chunks[0].model_copy(update={'id':'hidden','text':'Dữ liệu công khai. '*500})
    hidden.checksum=digest(hidden.text)
    doc.chunks.append(hidden)
    payload=release(store,[doc])
    state=approved_state(payload,[doc],date(2026,10,21))
    state['evidence'].append(Evidence(document=doc,chunk=hidden,applicability='current'))
    state['admitted_source_ids']={doc.chunks[0].id}|({'hidden'} if admitted else set())
    state['synthesis_sources']={doc.chunks[0].id:context_item(doc)}
    state['draft']=Draft(status='answered',claims=[Claim(text='Một kết luận không có căn cứ được gửi synthesis.',citation_ids=['hidden'])])
    state['verification']=Verification(supported_claim_indexes=[0],supporting_quotes=[SupportingQuote(
        claim_index=0,citation_id='hidden',quote='Dữ liệu công khai. Dữ liệu công khai.')])
    await Agent(store,FakeProvider(settings)).finish(state)
    assert state['result'].status=='insufficient_evidence' and not state['result'].citations


async def test_finish_rechecks_exposure_without_recomputing_selection(store,settings,monkeypatch):
    doc=document();payload=release(store,[doc])
    state=approved_state(payload,[doc],date(2026,10,21))
    state['synthesis_sources']={}
    state['admitted_source_ids']={doc.chunks[0].id}
    agent=Agent(store,FakeProvider(settings))
    monkeypatch.setattr(agent,'prompt_context',lambda *args:pytest.fail('Must use frozen exposure, not repack'))
    await agent.finish(state)
    assert state['result'].status=='insufficient_evidence' and not state['result'].verified_claims


async def test_proof_from_unexposed_part_of_selected_id_is_rejected_at_finish(store,settings):
    raw='Điều 1. Nguồn công khai. 1. Phạm vi được cung cấp đầy đủ. 2. Chi tiết chưa gửi model này.'
    doc=document(text=raw);payload=release(store,[doc])
    state=approved_state(payload,[doc],date(2026,10,21))
    state['admitted_source_ids']={doc.chunks[0].id}
    state['synthesis_sources']={doc.chunks[0].id:{**context_item(doc),'text':'1. Phạm vi được cung cấp đầy đủ.'}}
    state['verification']=Verification(supported_claim_indexes=[0],supporting_quotes=[SupportingQuote(
        claim_index=0,citation_id=doc.chunks[0].id,quote='2. Chi tiết chưa gửi model này.')])
    await Agent(store,FakeProvider(settings)).finish(state)
    assert state['result'].status=='insufficient_evidence' and not state['result'].citations


async def test_real_run_cannot_release_claim_without_synthesis_ledger(store,settings):
    release(store)
    class OmitSynthesis(Agent):
        async def synthesize(self,state):
            state['draft']=Draft(status='answered',claims=[Claim(text='Kết luận không qua synthesis.',citation_ids=['law-1'])])
            return state
    result=await OmitSynthesis(store,FakeProvider(settings)).run(ChatRequest(session_id='0'*36,message='Điều kiện bồi thường?'),noop)
    assert result.status=='insufficient_evidence' and not result.citations


@pytest.mark.parametrize('use_parent',[True,False])
async def test_only_exposed_parent_alias_is_citable_not_contained_hidden_child(store,settings,use_parent):
    doc=document()
    child=doc.chunks[0];child.parent_id='law-parent'
    parent=child.model_copy(update={'id':'law-parent','parent_id':None,
        'text':child.text+' Điều kiện tiếp theo cũng cần được đối chiếu theo hồ sơ.'})
    parent.checksum=digest(parent.text)
    doc.chunks.append(parent)
    release(store,[doc])
    provider=AliasProvider(settings,hidden_id=None if use_parent else child.id)
    result=await Agent(store,provider).run(ChatRequest(session_id='0'*36,message='Điều kiện bồi thường?'),noop)
    assert result.status==('answered' if use_parent else 'insufficient_evidence')
    if use_parent:assert [c.id for c in result.citations]==[parent.id]
    else:assert not result.citations


async def test_missing_modifier_due_to_budget_remains_unpublishable(store,settings):
    base=document('original')
    modifier=document('modifier',text='Nội dung tác động chưa chia khoản. '+('nội dung công khai '*500))
    release(store,[base,modifier],relations=[{'source_id':modifier.id,'target_id':base.id,
        'type':'amends','source_locator':'Điều 1','target_locators':['Điều 1'],'target_locators_complete':True,
        'source_url':str(modifier.url),'explanation':'A verified source relationship.'}])
    provider=AliasProvider(settings)
    result=await Agent(store,provider).run(ChatRequest(session_id='0'*36,message='Điều kiện bồi thường?'),noop)
    assert result.status=='insufficient_evidence' and not result.citations
    assert any('sửa đổi' in event.summary for event in result.trace)


async def test_verifier_receives_and_checks_only_exposed_source_spans(store,settings):
    source=('Điều 1. Nguồn công khai. 1. Điều kiện bồi thường được kiểm tra theo hồ sơ. '
            '2. Nội dung khác chỉ cung cấp khi có căn cứ riêng.')
    doc=document(text=source);payload=release(store,[doc])
    state=approved_state(payload,[doc],date(2026,10,21))
    shown='1. Điều kiện bồi thường được kiểm tra theo hồ sơ.'
    state['synthesis_sources']={doc.chunks[0].id:{**context_item(doc),'text':shown}}
    state['admitted_source_ids']={doc.chunks[0].id}
    class HiddenQuote(FakeProvider):
        async def generate(self,schema,instruction,payload,budget):
            assert schema is Verification
            assert all('2. Nội dung khác' not in span['quote'] for span in payload['source_spans'])
            return Verification(supported_claim_indexes=[0],supporting_quotes=[SupportingQuote(
                claim_index=0,citation_id=payload['draft']['claims'][0]['citation_ids'][0],
                quote='2. Nội dung khác chỉ cung cấp khi có căn cứ riêng.')])
    agent=Agent(store,HiddenQuote(settings))
    await agent.verify(state);await agent.finish(state)
    assert state['result'].status=='insufficient_evidence' and not state['result'].citations


def test_other_article_amendment_does_not_get_dependency_priority():
    base=context_item(document('base',text='Điều 1. Quy định đang hỏi.'))
    unrelated=context_item(document('modifier',text='Sửa đổi Điều 77, không phải điều đang hỏi.'))
    unrelated['legal_relations']=[{'source_id':'modifier','target_id':'base','type':'amends',
        'source_locator':'Điều 1','target_locators':['Điều 77'],'target_locators_complete':True}]
    noise=[context_item(document(f'extra-{i}',text='Nội dung khác. '*90)) for i in range(10)]
    passages,docs,reasons=pack([base,*noise,unrelated])
    selected_ids=[p['citation_id'] for p in passages]
    if unrelated['citation_id'] in selected_ids:
        assert all(selected_ids.index(item['citation_id'])<selected_ids.index(unrelated['citation_id'])
                   for item in noise if item['citation_id'] in selected_ids)
    assert wire_size(passages,docs)<=7000


def test_runtime_fingerprint_binds_context_selection_module(settings,monkeypatch):
    from pathlib import Path
    from landlaw.evaluation import configuration_fingerprint
    original=Path.read_bytes
    before=configuration_fingerprint(settings)
    def changed(path):
        content=original(path)
        return content+b'\n# changed context selection\n' if path.name=='synthesis_context.py' else content
    monkeypatch.setattr(Path,'read_bytes',changed)
    assert configuration_fingerprint(settings)!=before


async def test_projected_source_with_explicit_omission_can_be_verified(store,settings):
    raw=('Điều 1. Nội dung công khai để đối chiếu. 1. Phạm vi khác không được hỏi. '
         '2. Điều kiện bồi thường phải được kiểm tra theo hồ sơ. '
         '3. Cơ quan báo cáo định kỳ.')
    doc=document(text=raw);payload=release(store,[doc])
    state=approved_state(payload,[doc],date(2026,10,21))
    view=paragraph_view(context_item(doc),'điều kiện bồi thường',model_passage_text,source_clause_spans,{'2'})
    state['draft']=Draft(status='answered',claims=[Claim(text='Điều kiện bồi thường phải được kiểm tra theo hồ sơ.',citation_ids=[doc.chunks[0].id])])
    state['synthesis_sources']={doc.chunks[0].id:view}
    state['admitted_source_ids']={doc.chunks[0].id}
    agent=Agent(store,FakeProvider(settings))
    await agent.verify(state);await agent.finish(state)
    assert state['result'].status=='answered' and state['result'].citations
    assert state['synthesis_diagnostics']['released_citations']==[doc.chunks[0].id]


def test_future_amendment_is_not_packed_ahead_of_current_evidence():
    base=context_item(document('base',text='Điều 1. Quy định đang hỏi.'))
    future=context_item(document('future',text='Điều 1. Sửa đổi điều kiện trong tương lai.'))
    future['legal_relations']=[{'source_id':'future','target_id':'base','type':'amends',
        'source_locator':'Điều 1','target_locators':['Điều 1'],'target_locators_complete':True,
        'source_effective_from':'2027-01-01'}]
    noise=[context_item(document(f'extra-{i}',text='Nội dung đang áp dụng. '*70)) for i in range(7)]
    passages,docs,_=pack([base,*noise,future])
    ids=[p['citation_id'] for p in passages]
    if future['citation_id'] in ids:
        assert all(ids.index(item['citation_id'])<ids.index(future['citation_id']) for item in noise if item['citation_id'] in ids)


async def test_direct_finish_without_exposure_ledger_fails_closed(store,settings):
    doc=document();payload=release(store,[doc])
    state=approved_state(payload,[doc],date(2026,10,21))
    state.pop('synthesis_sources',None)
    await Agent(store,FakeProvider(settings)).finish(state)
    assert state['result'].status=='insufficient_evidence' and not state['result'].citations
    assert any('ledger' in issue for issue in state['verification'].issues)
