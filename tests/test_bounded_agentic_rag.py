"""Bounded Agentic RAG: model-driven tool choice, context and release guards."""
import asyncio

import pytest

from conftest import document, release, session
from landlaw.agentic_rag import BoundedAgenticRAG
from landlaw.conversation import contextual_retrieval_query
from landlaw.models import ChatRequest
from landlaw.simple_rag import SimpleAnswer


class ToolProvider:
    configured = True

    def __init__(self, settings, decisions, answer=None):
        self.settings = settings
        self.decisions = list(decisions)
        self.answer = answer or SimpleAnswer(answer="Theo nguồn, điều kiện cần kiểm tra theo hồ sơ [S1].")
        self.tool_steps = 0
        self.generations = 0

    async def embed(self, *args, **kwargs):
        budget = kwargs.get("budget")
        if budget is not None:
            budget.embedding_calls += 1
        return []

    async def tool_step(self, instruction, messages, tools, budget, **kwargs):
        self.tool_steps += 1
        budget.llm()
        assert tools and tools[0]["function"]["name"] == "search_legal_evidence"
        return self.decisions.pop(0)

    async def generate(self, schema, instruction, payload, budget, **kwargs):
        self.generations += 1
        budget.llm()
        assert schema is SimpleAnswer
        return self.answer


def request(session_id, message, history=None):
    return ChatRequest(session_id=session_id, message=message, history=history or [], mode="agentic_rag")


def tool_call(name, arguments, call_id="call-1"):
    return {"id": call_id, "name": name, "arguments": arguments}


def test_social_turn_is_direct_and_never_retrieves(store, settings):
    release(store, [document()])
    sid, _ = session(store)
    provider = ToolProvider(settings, [{"content": "Xin chào! Mình có thể giúp gì cho bạn?", "tool_calls": []}])
    result = asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, "Xin chào"), lambda _: None, "r1"))
    assert result.status == "answered"
    assert "Xin chào" in result.content
    assert result.llm_calls == 1 and result.embedding_calls == 0
    assert provider.generations == 0 and result.citations == []


def test_legal_question_uses_search_tool_then_grounded_generation(store, settings):
    release(store, [document(text="Điều 95. Điều kiện được bồi thường về đất khi thu hồi đất.",
                             locator="Điều 95")])
    sid, _ = session(store)
    provider = ToolProvider(settings, [
        {"content": "", "tool_calls": [tool_call("search_legal_evidence", '{"query":"điều kiện bồi thường"}')]},
        {"content": "", "tool_calls": []},
    ], answer=SimpleAnswer(answer="Bạn cần kiểm tra điều kiện được bồi thường theo Điều 95 [S1]."))
    result = asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, "Tôi có được bồi thường khi thu hồi đất không?"), lambda _: None, "r1"))
    assert result.status == "answered"
    assert result.verified_claims and result.citations
    assert result.citations[0].locator == "Điều 95"
    assert result.tool_calls == 1
    assert result.llm_calls == 2  # one tool decision + one grounded generation
    assert result.evidence_chunk_ids == [result.citations[0].id]
    assert provider.tool_steps == 1 and provider.generations == 1


def test_legal_model_direct_answer_is_forced_through_retrieval(store, settings):
    release(store, [document(text="Điều 95. Điều kiện được bồi thường về đất khi thu hồi đất.",
                             locator="Điều 95")])
    sid, _ = session(store)
    provider = ToolProvider(settings, [{"content": "Bạn chắc chắn được bồi thường.", "tool_calls": []}],
                            answer=SimpleAnswer(answer="Theo Điều 95, điều kiện được bồi thường cần kiểm tra [S1]."))
    result = asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, "Tôi có được bồi thường khi thu hồi đất không?"), lambda _: None, "r1"))
    assert result.status == "answered"
    assert "Theo Điều 95" in result.content
    assert result.llm_calls == 2  # one tool decision + one grounded generation
    assert result.embedding_calls == 1


def test_unknown_article_reference_is_rejected(store, settings):
    release(store, [document(text="Điều 95. Điều kiện được bồi thường về đất khi thu hồi đất.",
                             locator="Điều 95")])
    sid, _ = session(store)
    provider = ToolProvider(settings, [
        {"content": "", "tool_calls": [tool_call("search_legal_evidence", '{"query":"bồi thường"}')]},
        {"content": "", "tool_calls": []},
    ], answer=SimpleAnswer(answer="Bạn phải xem Điều 107 để biết trường hợp không được bồi thường [S1]."))
    result = asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, "Tôi có được bồi thường không?"), lambda _: None, "r1"))
    assert result.status == "clarification_needed"
    assert "chưa thể xác nhận" in result.content


def test_added_specific_condition_without_source_is_rejected(store, settings):
    release(store, [document(text="Điều 95. Điều kiện được bồi thường về đất khi thu hồi đất.",
                             locator="Điều 95")])
    sid, _ = session(store)
    provider = ToolProvider(settings, [
        {"content": "", "tool_calls": [tool_call("search_legal_evidence", '{"query":"bồi thường"}')]},
        {"content": "", "tool_calls": []},
    ], answer=SimpleAnswer(answer="Bạn được bồi thường nếu không vi phạm quy định về cư trú [S1]."))
    result = asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, "Tôi có được bồi thường không?"), lambda _: None, "r1"))
    assert result.status == "clarification_needed"


def test_wrong_paragraph_identity_is_rejected(store, settings):
    release(store, [document(text="Điều 95. Điều kiện được bồi thường. 2. Các trường hợp được bồi thường.",
                             locator="Điều 95")])
    sid, _ = session(store)
    provider = ToolProvider(settings, [
        {"content": "", "tool_calls": [tool_call("search_legal_evidence", '{"query":"bồi thường"}')]},
        {"content": "", "tool_calls": []},
    ], answer=SimpleAnswer(answer="Theo khoản 1 Điều 95, bạn cần đáp ứng điều kiện [S1]."))
    result = asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, "Tôi có được bồi thường không?"), lambda _: None, "r1"))
    assert result.status == "clarification_needed"


def test_wrong_document_identity_is_rejected(store, settings):
    release(store, [document(text="Điều 17. Hỗ trợ ổn định đời sống khi thu hồi đất.",
                             locator="Điều 17", document_number="40/2026/QĐ-UBND")])
    sid, _ = session(store)
    provider = ToolProvider(settings, [
        {"content": "", "tool_calls": [tool_call("search_legal_evidence", '{"query":"hỗ trợ ổn định đời sống"}')]},
        {"content": "", "tool_calls": []},
    ], answer=SimpleAnswer(answer="Theo Nghị định 49/2026/NĐ-CP, mức hỗ trợ là 12 tháng [S1]."))
    result = asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, "Hỗ trợ ổn định đời sống là bao lâu?"), lambda _: None, "r1"))
    assert result.status == "clarification_needed"


def test_negated_certainty_is_allowed_but_absolute_claim_is_not():
    from landlaw.legal_text import confidence_issues
    assert confidence_issues("Tôi chưa thể xác nhận câu trả lời tự động đủ chắc chắn.") == []
    assert confidence_issues("Bạn chắc chắn được bồi thường.") != []


def test_project_news_cannot_prove_household_entitlement(store, settings):
    release(store, [document(doc_id='ring4-news', source_kind='official_news',
                             text='Dự án Vành đai 4 đang được đẩy nhanh tiến độ giải phóng mặt bằng.',
                             locator='Tin dự án')])
    sid, _ = session(store)
    provider = ToolProvider(settings, [
        {"content": "", "tool_calls": [tool_call("search_legal_evidence", '{"query":"Vành đai 4 bồi thường"}')]},
        {"content": "", "tool_calls": []},
    ], answer=SimpleAnswer(answer="Theo tin dự án, hộ gia đình sẽ được bồi thường và bố trí tái định cư [S1]."))
    result = asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, "Đất tôi thuộc dự án Vành đai 4 thì được bồi thường thế nào?"), lambda _: None, "r1"))
    assert result.status == "clarification_needed"


def test_missing_evidence_returns_one_targeted_clarification(store, settings):
    release(store, [document(text="Nội dung không liên quan.")])
    sid, _ = session(store)
    provider = ToolProvider(settings, [
        {"content": "", "tool_calls": [tool_call("search_legal_evidence", '{"query":"quy hoạch vành đai"}')]},
        {"content": "", "tool_calls": []},
    ])
    result = asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, "Nhà tôi ở diện quy hoạch Vành đai 4 thì có được bố trí chỗ ở mới không?"),
        lambda _: None, "r1"))
    assert result.status == "clarification_needed"
    assert "quyết định thu hồi" in result.content
    assert result.support_level == "insufficient"


def test_tool_execution_cap_is_two(store, settings):
    release(store, [document(text="Điều 95. Điều kiện được bồi thường về đất khi thu hồi đất.",
                             locator="Điều 95")])
    sid, _ = session(store)
    provider = ToolProvider(settings, [
        {"content": "", "tool_calls": [
            tool_call("search_legal_evidence", '{"query":"bồi thường"}', "c1"),
            tool_call("open_legal_provision", '{"document_id":"law","locator":"Điều 95"}', "c2"),
        ]},
    ], answer=SimpleAnswer(answer="Theo Điều 95, điều kiện được bồi thường cần kiểm tra [S1]."))
    result = asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, "Tôi có được bồi thường không?"), lambda _: None, "r1"))
    assert result.tool_calls == 2
    assert result.llm_calls == 2  # one tool decision + one grounded generation
    assert provider.tool_steps == 1


def test_contextual_retrieval_query_inherits_short_follow_ups_only():
    from types import SimpleNamespace
    history = [SimpleNamespace(role="user", content="Nhà tôi bị thu hồi đất ở làm Vành đai 4."),
               SimpleNamespace(role="assistant", content="Cần xem xét hồ sơ.")]
    inherited, flag = contextual_retrieval_query("Vậy nếu chưa có sổ đỏ thì sao?", history)
    assert flag and "Nhà tôi bị thu hồi" in inherited
    inherited, flag = contextual_retrieval_query("Còn đất nông nghiệp?", history)
    assert flag
    standalone, flag = contextual_retrieval_query("Điều kiện tái định cư là gì?", history)
    assert standalone == "Điều kiện tái định cư là gì?" and not flag
