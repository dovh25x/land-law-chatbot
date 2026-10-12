from datetime import date, timedelta

import pytest

from landlaw.agent import Agent, Plan, ToolCall, Verification, applicability
from landlaw.models import ChatRequest, Claim, Draft
from landlaw.provider import BudgetExceeded, ProviderUnavailable
from landlaw.security import utcnow
from landlaw.store import RateLimited
from conftest import document, release, session


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
        from landlaw.agent import SupportingQuote
        quotes=[SupportingQuote(claim_index=i,citation_id=citation_id,quote=e['text'][:1600])
            for i,claim in enumerate(payload['draft']['claims']) for citation_id in claim['citation_ids']
            for e in payload['evidence'] if e['citation_id']==citation_id]
        return self.verification.model_copy(update={'supporting_quotes':quotes})
    async def embed(self, *args, **kwargs):
        raise ProviderUnavailable("Embedding offline in test")


async def noop(_):
    pass


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


async def test_graph_calls_tools_and_verifies_before_answer(store, settings):
    release(store)
    sid, _ = session(store)
    events = []
    async def capture(event):
        events.append(event.step)
    result = await Agent(store, FakeProvider(settings)).run(ChatRequest(session_id=sid, message="Điều kiện bồi thường?"), capture)
    assert result.status == "answered"
    assert result.citations[0].id == "law-1"
    assert result.llm_calls == 3 and result.tool_calls >= 2
    assert events.index("synthesis") < events.index("verification")


async def test_invalid_citation_removed_not_rendered(store, settings):
    release(store)
    sid, _ = session(store)
    draft = Draft(status="answered", summary="Kết quả", claims=[Claim(text="Nội dung không hợp lệ", citation_ids=["hallucinated"])])
    result = await Agent(store, FakeProvider(settings, draft)).run(ChatRequest(session_id=sid, message="bồi thường"), noop)
    assert result.status == "insufficient_evidence"
    assert not result.citations and "Nội dung không hợp lệ" not in result.content


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
            if any(e['citation_id']=='new-1' for e in payload['evidence']):
                return Verification(supported_claim_indexes=[0],supporting_quotes=[SupportingQuote(
                    claim_index=0,citation_id='new-1',quote=docs[-1].chunks[0].text)])
            return Verification(needs_more_evidence=True,followup_query='new',issues=['Cần chứng cứ mới'])
    result=await Agent(store,Fresh(settings)).run(ChatRequest(session_id=sid,message='bồi thường'),noop)
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
