import asyncio
from datetime import date

import pytest
from fastapi.testclient import TestClient

from landlaw.api import create_app
from landlaw.models import ChatRequest
from landlaw.provider import ProviderUnavailable
from landlaw.simple_rag import SimpleAnswer, SimpleRAG, _marker_ids
from landlaw.store import RateLimited
from conftest import release, session


class SimpleProvider:
    configured = True

    def __init__(self, settings, *, failure=None, answer=None):
        self.settings = settings
        self.failure = failure
        self.answer = answer or SimpleAnswer(
            answer="Theo nguồn đã tra cứu, điều kiện này cần được xem xét theo hồ sơ [S1].",
        )
        self.calls = 0

    async def embed(self, *args, **kwargs):
        return []

    async def generate(self, schema, instruction, payload, budget, **kwargs):
        self.calls += 1
        budget.llm()
        if self.failure:
            raise self.failure
        assert schema is SimpleAnswer
        assert payload["allowed_citation_ids"]
        return self.answer


def request(session_id, message, history=None):
    return ChatRequest(session_id=session_id, message=message, history=history or [], mode="simple_rag")


@pytest.mark.parametrize(
    "message",
    [
        "Điều kiện bồi thường khi thu hồi đất là gì?",
        "Tôi có giấy chứng nhận quyền sử dụng đất thì được bồi thường không?",
        "Không có giấy chứng nhận thì sao?",
        "Sau khi thu hồi đất nông nghiệp có được hỗ trợ gì?",
        "Điều kiện tái định cư là gì?",
        "Tôi muốn biết quy định về hỗ trợ.",
        "Gia đình tôi cần chuẩn bị giấy tờ gì?",
    ],
)
def test_supported_questions_use_one_simple_generation(store, settings, message):
    from conftest import document
    release(store, [document(text="Điều kiện bồi thường thu hồi đất; giấy chứng nhận; hỗ trợ đất nông nghiệp; tái định cư; hồ sơ giấy tờ.")])
    sid, _ = session(store)
    provider = SimpleProvider(settings)
    result = asyncio.run(SimpleRAG(store, provider).run(request(sid, message), lambda _: None, "r1"))
    assert result.status == "answered"
    assert result.llm_calls == 1
    assert result.citations and result.citations[0].id == "law-1"
    assert provider.calls == 1


def test_greeting_does_not_retrieve_or_call_model(store, settings):
    release(store)
    sid, _ = session(store)
    provider = SimpleProvider(settings)
    result = asyncio.run(SimpleRAG(store, provider).run(request(sid, "Xin chào!"), lambda _: None, "r1"))
    assert result.status == "answered"
    assert result.llm_calls == 0
    assert provider.calls == 0


def test_followup_sends_short_history_to_model(store, settings):
    from conftest import document
    release(store, [document(text="Điều kiện bồi thường thu hồi đất; giấy chứng nhận; hỗ trợ đất nông nghiệp; tái định cư; hồ sơ giấy tờ.")])
    sid, _ = session(store)
    provider = SimpleProvider(settings)
    history = [
        {"role": "user", "content": "Tôi hỏi về bồi thường."},
        {"role": "assistant", "content": "Bạn muốn hỏi điều kiện nào?"},
    ]
    result = asyncio.run(SimpleRAG(store, provider).run(
        request(sid, "Còn nếu không có giấy chứng nhận?", history), lambda _: None, "r1"
    ))
    assert result.status == "answered"
    assert result.llm_calls == 1


def test_exact_amount_without_facts_can_be_qualified(store, settings):
    release(store)
    sid, _ = session(store)
    provider = SimpleProvider(settings, answer=SimpleAnswer(
        answer="Chưa thể xác định số tiền chỉ từ câu hỏi này; cần hồ sơ và nhiều điều kiện cụ thể [S1].",
        clarification_question="Bạn đang hỏi loại đất và thời điểm phương án nào?",
    ))
    result = asyncio.run(SimpleRAG(store, provider).run(
        request(sid, "Tôi sẽ được chính xác bao nhiêu tiền?"), lambda _: None, "r1"
    ))
    assert result.status == "answered"
    assert "loại đất" in result.content


def test_out_of_scope_is_handled_without_retrieval(store, settings):
    release(store)
    sid, _ = session(store)
    provider = SimpleProvider(settings)
    result = asyncio.run(SimpleRAG(store, provider).run(request(sid, "Thời tiết Hà Nội hôm nay?"), lambda _: None, "r1"))
    assert result.status == "clarification_needed"
    assert result.llm_calls == 0


@pytest.mark.parametrize("failure, expected", [
    (ProviderUnavailable("Không kết nối được Groq", retryable=True), "error"),
    (RateLimited(30), "limited"),
])
def test_provider_failures_are_distinguished(store, settings, failure, expected):
    release(store)
    sid, _ = session(store)
    provider = SimpleProvider(settings, failure=failure)
    result = asyncio.run(SimpleRAG(store, provider).run(
        request(sid, "Điều kiện bồi thường là gì?"), lambda _: None, "r1"
    ))
    assert result.status == expected


def test_chat_endpoint_routes_simple_rag_mode(store, settings):
    release(store)
    sid, token = session(store)
    provider = SimpleProvider(settings)
    with TestClient(create_app(settings, store, provider)) as client:
        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"session_id": sid, "message": "Điều kiện bồi thường là gì?", "mode": "simple_rag"},
        )
    assert response.status_code == 200
    assert "event: result" in response.text
    assert '"status": "answered"' in response.text
    assert provider.calls == 1


def test_inline_markers_are_the_only_citation_contract():
    assert _marker_ids("Ý thứ nhất [S1], ý thứ hai 【 S2 】 và lặp lại [ S1 ].") == (["S1", "S2"], False)
    assert _marker_ids("Nguồn không tồn tại [S9].")[1] is True


def test_multiple_inline_citations_are_derived_once_each(store, settings):
    from conftest import document
    release(store, [
        document(doc_id="law-1", text="Điều kiện bồi thường phải được xem xét theo hồ sơ."),
        document(doc_id="law-2", text="Khoản hỗ trợ được xác định theo điều kiện và hồ sơ."),
    ])
    sid, _ = session(store)
    provider = SimpleProvider(settings, answer=SimpleAnswer(
        answer="Điều kiện bồi thường cần được xem xét theo hồ sơ [S1]. Khoản hỗ trợ cũng phụ thuộc điều kiện [S2].",
    ))
    result = asyncio.run(SimpleRAG(store, provider).run(
        request(sid, "Điều kiện bồi thường và hỗ trợ là gì?"), lambda _: None, "r1"
    ))
    assert result.status == "answered"
    assert {citation.document_id for citation in result.citations} == {"law-1", "law-2"}


@pytest.mark.parametrize(
    "answer, expected_status, expected_citations",
    [
        ("Điều kiện bồi thường cần được xem xét theo hồ sơ [S1].", "answered", 1),
        ("Điều kiện bồi thường [S1].", "answered", 1),
        ("Bạn chắc chắn nhận 10 tỷ đồng [S1].", "clarification_needed", 1),
        ("Đền bù cho hộ của bạn 5 triệu đồng trên mỗi mét [S1].", "clarification_needed", 1),
        ("Câu trả lời không có nguồn.", "clarification_needed", 1),
        ("Bạn chắc chắn nhận 10 tỷ đồng [S9].", "clarification_needed", 1),
    ],
)
def test_citation_validation_requires_supported_inline_markers(
    store, settings, answer, expected_status, expected_citations
):
    from conftest import document
    release(store, [document(text="Điều kiện bồi thường và hỗ trợ cần được xem xét theo hồ sơ.")])
    sid, _ = session(store)
    provider = SimpleProvider(settings, answer=SimpleAnswer(answer=answer))
    result = asyncio.run(SimpleRAG(store, provider).run(
        request(sid, "Điều kiện bồi thường là gì?"), lambda _: None, "r1"
    ))
    assert result.status == expected_status
    assert len(result.citations) == expected_citations
    if expected_status == "clarification_needed":
        assert "chưa thể xác nhận" in result.content


def test_conditional_framing_keeps_grounded_answers_published(store, settings):
    from conftest import document
    release(store, [document(text="Điều kiện bồi thường và hỗ trợ cần được xem xét theo hồ sơ.")])
    sid, _ = session(store)
    provider = SimpleProvider(settings, answer=SimpleAnswer(
        answer="Bạn vẫn có thể được bồi thường nếu đủ điều kiện theo Điều 95 [S1]. "
               "Đây là câu trả lời có điều kiện vì bạn chưa nêu thời điểm thu hồi và loại đất [S1].",
    ))
    result = asyncio.run(SimpleRAG(store, provider).run(
        request(sid, "Điều kiện bồi thường là gì?"), lambda _: None, "r1"
    ))
    assert result.status == "answered"
    assert len(result.citations) == 1


def test_adjacent_inline_markers_do_not_invalidate_support(store, settings):
    from conftest import document
    release(store, [
        document(doc_id="law-1", text="Điều kiện bồi thường cần được xem xét theo hồ sơ."),
        document(doc_id="law-2", text="Hỗ trợ được xác định theo điều kiện của hồ sơ."),
    ])
    sid, _ = session(store)
    provider = SimpleProvider(settings, answer=SimpleAnswer(
        answer="Điều kiện bồi thường cần được xem xét theo hồ sơ [S1][S2].",
    ))
    result = asyncio.run(SimpleRAG(store, provider).run(
        request(sid, "Điều kiện bồi thường là gì?"), lambda _: None, "r1"
    ))
    assert result.status == "answered"
    assert {citation.document_id for citation in result.citations} == {"law-1", "law-2"}


def test_configured_simple_mode_routes_default_request(store, settings):
    release(store)
    sid, token = session(store)
    provider = SimpleProvider(settings)
    configured = settings.model_copy(update={"execution_mode": "simple_rag"})
    with TestClient(create_app(configured, store, provider)) as client:
        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"session_id": sid, "message": "Điều kiện bồi thường là gì?"},
        )
    assert response.status_code == 200
    assert '"status": "answered"' in response.text
    assert provider.calls == 1
