"""Deterministic reproductions for the legal-answer grounding hotfix.

The corpus fixture is a verbatim subset of the reviewed production snapshot
``corpus-1afca764aa6692e0`` (see its provenance header). Model output is mocked:
these tests exercise the application contract, not Groq quality.
"""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import session
from landlaw.agentic_rag import BoundedAgenticRAG
from landlaw.conversation import classify
from landlaw.legal_text import marker_ids, validate_answer_result
from landlaw.models import ChatRequest
from landlaw.provider import Budget, ProviderUnavailable
from landlaw.security import local_date
from landlaw.simple_rag import SimpleAnswer
from landlaw.store import RateLimited


FIXTURE = Path(__file__).parent / "fixtures" / "legal-answer-hotfix-release.json"
# Mirror frontend/src/citizen.ts; update together when the landing prompts change.
LEGAL_SUGGESTIONS = (
    ("Có sổ đỏ, khi Nhà nước thu hồi đất ở thì điều kiện được bồi thường là gì?",
     {("31/2024/QH15", "Điều 95"), ("40/2026/QĐ-UBND", "Điều 4")}),
    ("Khi bị thu hồi đất nông nghiệp, người dân có thể được hỗ trợ những gì?",
     {("88/2024/NĐ-CP", "Điều 19"), ("31/2024/QH15", "Điều 109")}),
    ("Nếu bị thu hồi đất ở và phải chuyển nhà, điều kiện được bố trí tái định cư là gì?",
     {("40/2026/QĐ-UBND", "Điều 21"), ("88/2024/NĐ-CP", "Điều 24"),
      ("31/2024/QH15", "Điều 111")}),
)
PURE_ANSWER = SimpleAnswer(
    answer="Bạn đã nhận được quyết định thu hồi đất hoặc thông báo thu hồi chưa?",
    clarification_question="Bạn đã nhận được quyết định thu hồi đất hoặc thông báo thu hồi chưa?",
)


def stage_reviewed_fixture(store, release_id="legal-hotfix-fixture"):
    payload = json.loads(FIXTURE.read_text())
    payload["id"] = release_id
    store.stage(payload)
    store.publish(release_id)
    return release_id


class ScenarioProvider:
    configured = True

    def __init__(self, settings, answer, query="bồi thường tái định cư", direct=None):
        self.settings = settings
        self.answer = answer
        self.query = query
        self.direct = direct
        self.tool_steps = 0
        self.generations = 0
        self.generation_attempts = None
        self.last_payload = None
        self.embedding_calls = 0

    async def embed(self, *args, **kwargs):
        self.embedding_calls += 1
        budget = kwargs.get("budget")
        if budget is not None:
            budget.embedding_calls += 1
        return []

    async def tool_step(self, instruction, messages, tools, budget, **kwargs):
        self.tool_steps += 1
        budget.llm()
        if self.direct is not None:
            return self.direct
        return {
            "content": "",
            "tool_calls": [{
                "id": "call-1",
                "name": "search_legal_evidence",
                "arguments": json.dumps({"query": self.query}, ensure_ascii=False),
            }],
        }

    async def generate(self, schema, instruction, payload, budget, **kwargs):
        self.generations += 1
        self.generation_attempts = kwargs.get("max_attempts")
        self.last_payload = payload
        budget.llm()
        assert schema is SimpleAnswer
        return self.answer


def request(session_id, message, history=None):
    return ChatRequest(
        session_id=session_id,
        message=message,
        history=history or [],
        mode="agentic_rag",
    )


def run_turn(store, provider, message, history=None):
    sid, _ = session(store)
    return asyncio.run(BoundedAgenticRAG(store, provider).run(
        request(sid, message, history), lambda _: None, "legal-hotfix-fixture"))


def published_fallback(result) -> bool:
    return any(event.step == "clarification" and "Safe clarification fallback" in event.summary
               for event in result.trace)


@pytest.fixture
def reviewed_store(store):
    stage_reviewed_fixture(store)
    return store


def test_t01_planning_area_gets_a_grounded_conditional_answer(reviewed_store, settings):
    answer = SimpleAnswer(
        answer=("Việc nằm trong vùng quy hoạch chưa đủ để kết luận về tái định cư. "
                "Khi Nhà nước thu hồi đất ở và hộ đủ điều kiện bồi thường về đất ở, việc bố trí tái định cư "
                "được thực hiện theo phương án đã được phê duyệt [S1]. "
                "Bạn đã nhận quyết định thu hồi đất hoặc thông báo thu hồi chưa?"),
        clarification_question="Bạn đã nhận quyết định thu hồi đất hoặc thông báo thu hồi chưa?",
        limitation="Đây là quy định chung; quyền lợi cụ thể phụ thuộc hồ sơ và phương án của dự án.",
    )
    result = run_turn(
        reviewed_store,
        ScenarioProvider(settings, answer, query="quy hoạch Vành đai 4 bố trí tái định cư"),
        "Nhà tôi nằm trong khu vực quy hoạch đường Vành đai 4 Hà Nội, tôi có được bố trí tái định cư không?",
    )
    assert result.status == "answered"
    assert result.citations and result.verified_claims
    assert [(citation.document_number, citation.locator) for citation in result.citations] == [
        ("88/2024/NĐ-CP", "Điều 24")]
    assert "quy hoạch" in result.content.casefold()
    assert "quyết định thu hồi" in result.content
    assert not published_fallback(result)
    assert result.llm_calls == 2


def test_t02_missing_certificate_still_gets_a_conditional_answer(reviewed_store, settings):
    answer = SimpleAnswer(
        answer=("Có giấy chứng nhận quyền sử dụng đất là một căn cứ quan trọng để xét điều kiện được bồi thường "
                "về đất khi Nhà nước thu hồi đất [S1]. Trường hợp không có giấy chứng nhận vẫn có thể được xét "
                "theo quy định về giấy tờ và nguồn gốc sử dụng đất [S1]. Bạn đang có loại giấy tờ nào?"),
        clarification_question="Bạn đang có loại giấy tờ nào?",
    )
    result = run_turn(
        reviewed_store,
        ScenarioProvider(settings, answer, query="không có sổ đỏ điều kiện bồi thường về đất"),
        "Tôi không có sổ đỏ thì có được bồi thường về đất khi thu hồi không?",
    )
    assert result.status == "answered"
    assert [(citation.document_number, citation.locator) for citation in result.citations] == [
        ("88/2024/NĐ-CP", "Điều 5")]
    assert not published_fallback(result)
    assert "giấy tờ" in result.content.casefold()


def test_l01_registered_land_answer_does_not_fall_back(reviewed_store, settings):
    answer = SimpleAnswer(
        answer=("Khi Nhà nước thu hồi hết đất ở hoặc phần diện tích đất ở còn lại nhỏ hơn diện tích tối thiểu "
                "được phép tách thửa, hộ gia đình đủ điều kiện được bồi thường có thể được bồi thường bằng "
                "giao đất ở có thu tiền sử dụng đất, mua nhà ở tái định cư hoặc bằng tiền [S3]. "
                "Điều kiện bồi thường còn phụ thuộc giấy tờ và nguồn gốc của thửa đất; bạn đang có loại giấy tờ nào?"),
        clarification_question="Bạn đang có loại giấy tờ nào?",
    )
    result = run_turn(
        reviewed_store,
        ScenarioProvider(settings, answer, query="sổ đỏ bồi thường đất ở thu hồi"),
        "Tôi có sổ đỏ, khi thu hồi đất có được bồi thường không?",
    )
    assert result.status == "answered"
    assert [(citation.document_number, citation.locator) for citation in result.citations] == [
        ("40/2026/QĐ-UBND", "Điều 4")]
    assert not published_fallback(result)


def test_direct_local_law_precedes_transitional_resolution_and_uses_distinct_locators(
        reviewed_store, settings):
    provider = ScenarioProvider(
        settings, PURE_ANSWER, query="sổ đỏ bồi thường đất ở thu hồi")
    result = run_turn(
        reviewed_store, provider,
        "Tôi có sổ đỏ, khi thu hồi đất có được bồi thường không?",
    )
    assert result.status == "clarification_needed"
    headers = [block.split("\n", 1)[0] for block in provider.last_payload["context"].split("\n\n")]
    assert headers and "tháo gỡ" not in headers[0].casefold()
    assert not any("254/2025" in header for header in headers)
    locators = [header.split(" — ")[2] for header in headers if " — " in header]
    assert len(locators) == len(set(locators))


def test_l02_giao_dat_resettlement_answer_is_published(reviewed_store, settings):
    answer = SimpleAnswer(
        answer=("Hộ gia đình đủ điều kiện bồi thường về đất ở có thể được bồi thường bằng giao đất ở tái định cư "
                "theo phương án đã được phê duyệt [S1, S2]. Bạn đã nhận được quyết định giao đất tái định cư chưa?"),
        clarification_question="Bạn đã nhận được quyết định giao đất tái định cư chưa?",
    )
    result = run_turn(
        reviewed_store,
        ScenarioProvider(settings, answer, query="quyết định giao đất tái định cư"),
        "Tôi đã nhận quyết định giao đất tái định cư, vậy có được bồi thường thêm không?",
    )
    assert result.status == "answered"
    assert [(citation.document_number, citation.locator) for citation in result.citations] == [
        ("31/2024/QH15", "Điều 111"), ("40/2026/QĐ-UBND", "Điều 21")]
    assert not published_fallback(result)


def test_l03_life_stabilization_support_answer_is_published(reviewed_store, settings):
    answer = SimpleAnswer(
        answer=("Hỗ trợ ổn định đời sống được xét cho hộ gia đình, cá nhân đang sử dụng đất nông nghiệp nếu đủ "
                "điều kiện được bồi thường về đất [S1]. Mức và thời gian hỗ trợ phụ thuộc quy định của địa phương "
                "và diện tích đất thu hồi [S1]. Bạn bị thu hồi bao nhiêu phần trăm diện tích đất nông nghiệp?"),
        clarification_question="Bạn bị thu hồi bao nhiêu phần trăm diện tích đất nông nghiệp?",
    )
    result = run_turn(
        reviewed_store,
        ScenarioProvider(settings, answer, query="hỗ trợ ổn định đời sống đất nông nghiệp"),
        "Hỗ trợ ổn định đời sống khi thu hồi đất nông nghiệp được tính thế nào?",
    )
    assert result.status == "answered"
    assert [(citation.document_number, citation.locator) for citation in result.citations] == [
        ("88/2024/NĐ-CP", "Điều 19")]
    assert not published_fallback(result)


def test_capabilities_suggestion_uses_social_control():
    # Mirror frontend/src/citizen.ts; the prompt should introduce capabilities,
    # not turn into a legal retrieval query.
    intent = classify("Trợ lý này có thể giúp gì?")
    assert intent.kind == "capabilities"


def test_citizen_legal_suggestions_have_admitted_evidence(reviewed_store, settings):
    """Landing prompts must be answerable from the reviewed fixture subset.

    The first landing prompt is a capabilities/social turn and is covered by
    the social-control test. These three must retrieve at least one directly
    relevant admitted provision; this checks coverage, not answer correctness.
    """
    payload = json.loads(FIXTURE.read_text())
    payload["id"] = "legal-hotfix-fixture"
    rag = BoundedAgenticRAG(reviewed_store, ScenarioProvider(settings, PURE_ANSWER))
    for question, expected in LEGAL_SUGGESTIONS:
        sid, _ = session(reviewed_store)
        evidence = asyncio.run(rag._retrieve(
            question, request(sid, question), payload, local_date(), Budget(), []))
        identities = {(item.document.document_number, item.chunk.locator)
                      for item in evidence}
        assert identities & expected, (question, identities)
        assert len(evidence) <= 5
        assert all(item.applicability in {'current', 'provision_specific', 'context'}
                   for item in evidence)


def test_claim_free_clarification_is_published_without_markers(reviewed_store, settings):
    answer = SimpleAnswer(
        answer="Bạn đã nhận được quyết định thu hồi đất hoặc thông báo thu hồi chưa?",
        clarification_question="Bạn đã nhận được quyết định thu hồi đất hoặc thông báo thu hồi chưa?",
    )
    result = run_turn(
        reviewed_store,
        ScenarioProvider(settings, answer, query="quy hoạch Vành đai 4 tái định cư"),
        "Nhà tôi trong vùng quy hoạch Vành đai 4 thì có được bố trí tái định cư không?",
    )
    assert result.status == "clarification_needed"
    assert result.content.startswith("Bạn đã nhận được quyết định thu hồi đất")
    assert "Dưới đây là trích đoạn" not in result.content
    assert "Nguồn liên quan đã được đối chiếu" not in result.content
    assert result.support_level == "insufficient"
    assert not published_fallback(result)
    assert any(event.step == "clarification" and "Claim-free clarification" in event.summary
               for event in result.trace)
    assert result.llm_calls == 2


def test_t02_claim_free_clarification_is_published_without_raw_excerpts(reviewed_store, settings):
    answer = SimpleAnswer(
        answer="Bạn đang có loại giấy tờ nào?",
        clarification_question="Bạn đang có loại giấy tờ nào?",
    )
    result = run_turn(
        reviewed_store,
        ScenarioProvider(settings, answer, query="không có sổ đỏ điều kiện bồi thường về đất"),
        "Tôi không có sổ đỏ thì có được bồi thường về đất khi thu hồi không?",
    )
    assert result.status == "clarification_needed"
    assert result.content == "Bạn đang có loại giấy tờ nào?"
    assert "Dưới đây là trích đoạn" not in result.content
    assert "Nguồn liên quan đã được đối chiếu" not in result.content
    assert not published_fallback(result)


def test_uncited_substantive_answer_is_withheld_without_raw_excerpts(reviewed_store, settings):
    answer = SimpleAnswer(answer="Hộ gia đình có sổ đỏ được bồi thường về đất khi Nhà nước thu hồi đất.")
    result = run_turn(
        reviewed_store,
        ScenarioProvider(settings, answer, query="bồi thường đất ở"),
        "Tôi có sổ đỏ thì có được bồi thường về đất không?",
    )
    assert result.status == "clarification_needed"
    assert "chưa thể xác nhận" in result.content
    assert "Dưới đây là trích đoạn" not in result.content
    assert published_fallback(result)
    summaries = " ".join(event.summary for event in result.trace)
    assert "missing_required_citation" in summaries
    # No draft text or source excerpt is copied into internal trace diagnostics.
    assert "Hộ gia đình có sổ đỏ" not in summaries


def test_grouped_and_full_width_markers_are_supported_but_unknown_ids_are_rejected(reviewed_store, settings):
    answer = SimpleAnswer(
        answer="Theo Điều 95 [S1, S3], điều kiện bồi thường về đất được xét theo giấy tờ và nguồn gốc đất.",
        limitation="",
    )
    result = run_turn(
        reviewed_store,
        ScenarioProvider(settings, answer, query="điều kiện bồi thường về đất"),
        "Điều kiện bồi thường về đất là gì?",
    )
    assert result.status == "answered"
    assert [(citation.document_number, citation.locator) for citation in result.citations] == [
        ("88/2024/NĐ-CP", "Điều 5"), ("31/2024/QH15", "Điều 95")]

    unknown = SimpleAnswer(answer="Theo Điều 95 [S1, S9], điều kiện bồi thường về đất được xét theo hồ sơ.")
    rejected = run_turn(
        reviewed_store,
        ScenarioProvider(settings, unknown, query="điều kiện bồi thường về đất"),
        "Điều kiện bồi thường về đất là gì?",
    )
    assert rejected.status == "clarification_needed"
    assert "unknown_citation_id" in " ".join(event.summary for event in rejected.trace)


def test_claim_signal_covers_common_legal_assertions_without_citing_framing():
    class Source:
        pass

    source = Source()
    source.chunk = SimpleNamespace(text="Điều 95. Hộ gia đình được bồi thường về đất khi đủ điều kiện.",
                                   locator="Điều 95")
    source.document = SimpleNamespace(document_number="31/2024/QH15", title="Luật Đất đai",
                                       source_kind="legal", checked_at=None, url="https://x",
                                       id="law", source_review_notes="", effective_from=None,
                                       effective_to=None, applicability_verified=True,
                                       provision_validity=[])
    source_map = {"S1": source}

    claim_free = validate_answer_result("Bạn đã nhận quyết định thu hồi đất chưa?", source_map)
    assert claim_free.valid and claim_free.clarification_only
    assert claim_free.reason_codes == ("legitimate_clarification",)

    # An interrogative use of "được hưởng" is not an absolute entitlement claim.
    question = validate_answer_result("Tôi có được hưởng bồi thường không?", source_map)
    assert question.valid and question.clarification_only
    assert question.reason_codes == ("legitimate_clarification",)

    for claim in (
        "Hỗ trợ ổn định đời sống được tính bằng 12 tháng.",
        "Hộ gia đình được bồi thường bằng đất ở tái định cư.",
        "Theo Điều 95, hộ gia đình phải đáp ứng điều kiện.",
        "Bồi thường thiệt hại về tài sản được thực hiện theo phương án.",
    ):
        result = validate_answer_result(claim, source_map)
        assert not result.valid, claim
        assert "missing_required_citation" in result.reason_codes

    framed = validate_answer_result("Mình cần biết bạn đang hỏi về bồi thường hay tái định cư.", source_map)
    assert framed.valid and framed.clarification_only


def test_social_control_remains_direct(reviewed_store, settings):
    provider = ScenarioProvider(
        settings,
        answer=SimpleAnswer(answer="không dùng"),
        direct={"content": "Xin chào! Mình có thể giúp gì cho bạn?", "tool_calls": []},
    )
    result = run_turn(reviewed_store, provider, "Xin chào")
    assert result.status == "answered"
    assert result.llm_calls == 1 and result.tool_calls == 0
    assert result.citations == [] and provider.generations == 0


def test_generation_is_single_attempt_and_calls_are_bounded(reviewed_store, settings):
    answer = SimpleAnswer(answer="Theo Điều 4 [S1], việc bồi thường về đất khi Nhà nước thu hồi cơ bản được thực hiện bằng tiền.")
    provider = ScenarioProvider(settings, answer, query="nguyên tắc bồi thường khi thu hồi đất")
    result = run_turn(reviewed_store, provider, "Nguyên tắc bồi thường khi thu hồi đất là gì?")
    assert result.status == "answered"
    assert provider.generation_attempts == 1
    assert provider.tool_steps == 1 and provider.generations == 1
    assert result.tool_calls == 1 and result.llm_calls == 2


def test_provider_429_is_a_bounded_limited_response(reviewed_store, settings):
    class LimitedProvider(ScenarioProvider):
        async def tool_step(self, *args, **kwargs):
            raise RateLimited(retry_after=17)

    result = run_turn(
        reviewed_store,
        LimitedProvider(settings, SimpleAnswer(answer="unused")),
        "Điều kiện bồi thường là gì?",
    )
    assert result.status == "limited"
    assert "17" in result.content
    assert result.llm_calls == 0
    assert result.tool_calls == 0


def test_provider_schema_failure_is_publicly_safe(reviewed_store, settings):
    class FailingProvider(ScenarioProvider):
        async def generate(self, *args, **kwargs):
            raise ProviderUnavailable("upstream payload leaked", format_failure=True)

    result = run_turn(
        reviewed_store,
        FailingProvider(settings, SimpleAnswer(answer="unused")),
        "Điều kiện bồi thường là gì?",
    )
    assert result.status == "error"
    assert "upstream payload leaked" not in result.content
    assert "generation_schema_failure" in " ".join(event.summary for event in result.trace)
    assert result.support_level == "insufficient"


def test_generation_budget_exhaustion_uses_safe_fallback(reviewed_store, settings):
    class BudgetProvider(ScenarioProvider):
        async def tool_step(self, instruction, messages, tools, budget, **kwargs):
            self.tool_steps += 1
            budget.llm()
            budget.llm()
            budget.llm()
            return {"content": "", "tool_calls": [{
                "id": "call-1", "name": "search_legal_evidence",
                "arguments": json.dumps({"query": "bồi thường tái định cư"})}]}

    result = run_turn(
        reviewed_store,
        BudgetProvider(settings, SimpleAnswer(answer="unused")),
        "Điều kiện bồi thường là gì?",
    )
    assert result.status == "clarification_needed"
    assert "generation_budget_exhausted" in " ".join(event.summary for event in result.trace)
    assert "Dưới đây là trích đoạn" not in result.content
