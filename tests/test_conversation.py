"""Deterministic social-intent regressions: no retrieval and no model call."""
import asyncio

import pytest

from conftest import release, session
from landlaw.conversation import classify
from landlaw.models import ChatRequest
from landlaw.simple_rag import SimpleRAG, SimpleAnswer


class CountingProvider:
    configured = True

    def __init__(self, settings):
        self.settings = settings
        self.embeds = 0
        self.generations = 0

    async def embed(self, *args, **kwargs):
        self.embeds += 1
        return []

    async def generate(self, schema, instruction, payload, budget, **kwargs):
        self.generations += 1
        budget.llm()
        return SimpleAnswer(answer="Điều kiện bồi thường cần xem xét theo hồ sơ [S1].")


def request(session_id, message, history=None):
    return ChatRequest(session_id=session_id, message=message, history=history or [], mode="simple_rag")


@pytest.mark.parametrize("message,kind", [
    ("Bạn là ai?", "identity"),
    ("Bạn tên gì vậy?", "identity"),
    ("Bạn có thể giúp gì cho tôi?", "capabilities"),
    ("Bạn làm được những gì?", "capabilities"),
    ("Chatbot này dùng để làm gì?", "capabilities"),
    ("Bạn có thể giúp mình không?", "capabilities"),
    ("Cảm ơn nhé!", "gratitude"),
    ("Xin cảm ơn bạn nhiều", "gratitude"),
    ("Tạm biệt", "farewell"),
    ("Chào bạn", "greeting"),
    ("Hello", "greeting"),
    ("Chào bạn, bạn có thể giúp mình không?", "capabilities"),
    ("Thời tiết Hà Nội hôm nay?", "out_of_scope"),
    ("Bạn có thể giúp tôi viết code Python không?", "out_of_scope"),
    ("Tôi cần hỏi", "ambiguous"),
    ("Hôm nay thế nào?", "ambiguous"),
    ("Tôi muốn hỏi thủ tục thế chấp đất tại ngân hàng", "legal"),
    ("Có tin tức gì về thu hồi đất không?", "legal"),
])
def test_social_and_ambiguous_intents(message, kind):
    assert classify(message).kind == kind


@pytest.mark.parametrize("message", [
    "Bạn có thể giúp tôi xác định điều kiện bồi thường theo Luật Đất đai không?",
    "Tôi muốn hỏi về hỗ trợ tái định cư",
    "Nhà tôi ở ven đê có được đền bù không?",
    "Không có sổ đỏ thì có được xem xét không?",
    "Cảm ơn, cho tôi hỏi về bồi thường",
    "Đất của tôi bị lấy thì sao?",
])
def test_real_legal_questions_stay_on_the_rag_path(message):
    assert classify(message).kind == "legal"


def test_legal_follow_up_uses_previous_question_context():
    history = [
        {"role": "user", "content": "Nhà tôi có sổ đỏ, bị thu hồi đất ở để làm Vành đai 4 Hà Nội thì có được bồi thường không?"},
        {"role": "assistant", "content": "Cần xem xét điều kiện và giấy tờ theo hồ sơ."},
    ]
    for message in ("Trường hợp đó thì sao?", "Vậy thì sao?", "Còn đất nông nghiệp?", "Vậy nếu chưa có sổ đỏ thì sao?"):
        assert classify(message, history).kind == "legal"


@pytest.mark.parametrize("message", [
    "Bạn là ai?",
    "Bạn có thể giúp gì cho tôi?",
    "Bạn làm được những gì?",
    "Cảm ơn nhé!",
    "Tạm biệt",
    "Chào bạn, bạn có thể giúp mình không?",
    "Thời tiết Hà Nội hôm nay?",
    "Tôi cần hỏi",
])
def test_social_requests_never_retrieve_or_call_the_model(store, settings, message):
    release(store)
    sid, _ = session(store)
    provider = CountingProvider(settings)
    result = asyncio.run(SimpleRAG(store, provider).run(request(sid, message), lambda _: None, "r1"))
    assert result.llm_calls == 0 and result.embedding_calls == 0
    assert provider.embeds == 0 and provider.generations == 0
    assert not result.citations
    if classify(message).kind in {"out_of_scope", "ambiguous"}:
        assert result.status == "clarification_needed"
    else:
        assert result.status == "answered"
    assert "insufficient_evidence" not in str(result.status)


def test_social_turn_does_not_read_the_corpus(settings):
    class ExplodingStore:
        def __getattr__(self, name):
            raise AssertionError(f"social turn touched store.{name}")

    provider = CountingProvider(settings)
    sid = "s" * 32
    result = asyncio.run(SimpleRAG(ExplodingStore(), provider).run(
        request(sid, "Xin chào"), lambda _: None))
    assert result.status == "answered" and result.corpus_release is None
    assert result.llm_calls == 0 and result.embedding_calls == 0
    assert provider.embeds == 0 and provider.generations == 0
