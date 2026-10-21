"""Small conversational RAG path with bounded, source-allowlisted citations."""

import asyncio
from datetime import date
import re
import time
import uuid

from pydantic import BaseModel, Field

from .models import AnswerSection, ChatResult, Citation, Claim, Evidence, TraceEvent
from .provider import Budget, ProviderUnavailable
from .store import RateLimited
from .request_budget import BudgetExceeded
from .security import local_date, redact
from .publication import public_status
from .source_policy import applicability, citation_source_url


class SimpleAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)
    clarification_question: str = Field(default="", max_length=400)
    limitation: str = Field(default="", max_length=500)


GREETING = re.compile(r"^(xin chao|xin chào|chao|chào|hello|hi|cam on|cảm ơn|xin cam on|xin cảm ơn)[!.? ]*$", re.I)
OUT_OF_SCOPE = re.compile(r"\b(thời tiết|thoi tiet|chứng khoán|chung khoan|nấu ăn|nau an|lập trình|lap trinh)\b", re.I)
SOURCE_MARKER = re.compile(r"[\[【]\s*S(\d+)\s*[\]】]", re.I)
WORD = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
STOP_WORDS = {
    "của", "cho", "được", "không", "nhà", "nước", "người", "đất", "khi",
    "theo", "với", "và", "hoặc", "này", "đó", "những", "một", "các",
    "trong", "đến", "từ", "về", "có", "là", "thì", "nếu", "phải",
}


def _citation(item: Evidence, as_of: date) -> Citation:
    return Citation(
        id=item.chunk.id,
        document_id=item.document.id,
        title=item.document.title,
        document_number=item.document.document_number,
        url=str(item.document.url),
        locator=item.chunk.locator,
        excerpt=item.chunk.text[:1200],
        checked_at=item.document.checked_at,
        applicability=applicability(item.document, as_of, item.chunk),
        source_review_notes=item.document.source_review_notes,
        source_kind=item.document.source_kind,
        page=item.chunk.page,
        source_url=citation_source_url(item),
    )


def _marker_ids(answer: str) -> tuple[list[str], bool]:
    """Normalize harmless bracket/spacing variants and reject unknown markers."""
    markers = [f"S{match.group(1)}" for match in SOURCE_MARKER.finditer(answer)]
    unknown = bool(re.search(r"[\[【]\s*S\d+\s*[\]】]", answer, re.I)
                   and any(int(identifier[1:]) > 5 for identifier in markers))
    return list(dict.fromkeys(markers)), unknown


def _support_tokens(text: str) -> set[str]:
    return {word.casefold() for word in WORD.findall(text) if word.casefold() not in STOP_WORDS}


def _markers_are_supported(answer: str, source_map: dict[str, Evidence], marker_ids: list[str]) -> bool:
    """Require each marked statement to share substantive terms with its cited passage."""
    spans = list(SOURCE_MARKER.finditer(answer))
    if not spans:
        return False
    start = 0
    for span in spans:
        marker_match = re.search(r"\d+", span.group())
        identifier = f"S{marker_match.group()}" if marker_match else ""
        if identifier not in marker_ids:
            return False
        statement = answer[start:span.start()]
        if not (_support_tokens(statement) & _support_tokens(source_map[identifier].chunk.text)):
            return False
        start = span.end()
    return True


def _citation_fallback(source_map: dict[str, Evidence]) -> str:
    selected = list(source_map.items())[:2]
    lines = [
        "Tôi đã tìm thấy nguồn liên quan nhưng chưa thể xác nhận câu trả lời tự động đủ chắc chắn.",
        "Dưới đây là trích đoạn để bạn đối chiếu; đây chưa phải kết luận về quyền lợi của hồ sơ cụ thể:",
    ]
    for _, item in selected:
        excerpt = " ".join(item.chunk.text.split())[:500]
        lines.append(f"- **{item.document.title} — {item.chunk.locator}:** “{excerpt}”")
    lines.append("Bạn có thể bổ sung loại đất, giấy tờ và thời điểm thu hồi để tôi tra cứu tiếp.")
    return "\n\n".join(lines)


class SimpleRAG:
    def __init__(self, store, provider):
        self.store, self.provider = store, provider

    async def run(self, request, emit, release_id=None):
        started = time.monotonic()
        budget = Budget()
        as_of = request.as_of or local_date()
        trace: list[TraceEvent] = []
        release = await asyncio.to_thread(self.store.release, release_id, True)
        publication = await asyncio.to_thread(
            self.store.publication, (release or {}).get("id")
        )
        base = dict(
            **public_status(release, publication),
            as_of=as_of,
            corpus_release=(release or {}).get("id"),
            trace_id=str(uuid.uuid4()),
            model=self.provider.settings.generation_model,
            embedding_model=(release or {}).get("embedding_model", self.provider.settings.embedding_model),
            mode="simple_rag",
        )
        if GREETING.fullmatch(request.message.strip()):
            return ChatResult(
                **base,
                status="answered",
                content="Xin chào! Tôi có thể giúp bạn tra cứu bồi thường, hỗ trợ và tái định cư trong phạm vi dự án Vành đai 4 Hà Nội. Bạn muốn hỏi vấn đề nào?",
                answer_notices=["Đây là trợ lý tra cứu nguồn, không thay thế tư vấn pháp lý cho hồ sơ cá nhân."],
                trace=[TraceEvent(step="conversation", summary="Greeting handled without retrieval")],
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        if OUT_OF_SCOPE.search(request.message):
            return ChatResult(
                **base,
                status="clarification_needed",
                content="Tôi chỉ hỗ trợ tra cứu bồi thường, hỗ trợ và tái định cư liên quan Vành đai 4 Hà Nội. Bạn có thể hỏi về điều kiện, giấy tờ hoặc quy trình trong phạm vi này.",
                trace=[TraceEvent(step="conversation", summary="Out-of-scope request declined without retrieval")],
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        if not self.provider.configured:
            raise ProviderUnavailable("GROQ_API_KEY chưa được cấu hình; chưa thể sinh câu trả lời")
        vector = await self.provider.embed(request.message, query=True, budget=budget, release=release)
        evidence = await asyncio.to_thread(
            self.store.search, request.message, vector, request.project, (release or {}).get("id"),
            self.provider.settings.embedding_model, as_of
        )
        gate = await asyncio.to_thread(self.store.source_gate, (release or {}).get("id"))
        if gate is not None:
            reviews = await asyncio.to_thread(
                self.store.scoped_source_reviews,
                release,
                [(item.document.id, item.chunk.id, item.chunk.checksum) for item in evidence],
                as_of,
            )
            evidence = [
                item for item in evidence
                if reviews.get(f"{item.document.id}:{item.chunk.id}") == "fresh"
            ]
        evidence = [
            item for item in evidence
            if applicability(item.document, as_of, item.chunk) in {"current", "provision_specific", "context"}
        ][:5]
        trace.append(TraceEvent(step="retrieval", summary=f"Selected {len(evidence)} reviewed passages",
                                document_ids=[item.document.id for item in evidence]))
        if not evidence:
            return ChatResult(
                **base,
                status="insufficient_evidence",
                content="Tôi chưa tìm thấy đoạn nguồn đã kiểm tra đủ để trả lời câu hỏi này. Bạn có thể nêu rõ hơn loại đất, giấy tờ hoặc giai đoạn đang hỏi.",
                trace=trace,
                embedding_calls=budget.embedding_calls,
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        source_map = {f"S{i}": item for i, item in enumerate(evidence, 1)}
        context = "\n\n".join(
            f"[{key}] {item.document.title} — {item.chunk.locator}\n{item.chunk.text}"
            for key, item in source_map.items()
        )
        history = "\n".join(f"{m.role}: {redact(m.content)}" for m in request.history[-4:])
        prompt = """Trả lời bằng tiếng Việt, thân thiện và trực tiếp. Chỉ dùng nguồn trong CONTEXT.
Nêu quy tắc chung và điều kiện/ngoại lệ quan trọng; nếu thiếu dữ kiện cá nhân thì nói rõ đây là câu trả lời có điều kiện
hoặc hỏi tối đa một câu ngắn. Không kết luận chắc chắn quyền lợi hoặc số tiền của một hộ cụ thể.
Gắn [S1]...[S5] ngay sau từng ý được nguồn hỗ trợ. Chỉ dùng các mã xuất hiện trong CONTEXT; không tạo URL, điều luật hay mã nguồn mới."""
        try:
            answer = await self.provider.generate(
                SimpleAnswer, prompt,
                {"question": request.message, "history": history, "context": context,
                 "allowed_citation_ids": list(source_map)},
                budget, max_attempts=1
            )
        except RateLimited as exc:
            return ChatResult(**base, status="limited",
                content=f"Nhà cung cấp AI đang giới hạn lượt dùng. Vui lòng thử lại sau {exc.retry_after} giây.",
                trace=trace, embedding_calls=budget.embedding_calls, llm_calls=budget.llm_calls,
                token_usage=budget.tokens, elapsed_ms=int((time.monotonic()-started)*1000))
        except BudgetExceeded:
            return ChatResult(**base, status="limited",
                content="Lượt hỏi đã đạt giới hạn thực thi. Vui lòng tách câu hỏi và thử lại.",
                trace=trace, embedding_calls=budget.embedding_calls, llm_calls=budget.llm_calls,
                token_usage=budget.tokens, elapsed_ms=int((time.monotonic()-started)*1000))
        except ProviderUnavailable as exc:
            return ChatResult(**base, status="error", content=str(exc), trace=trace,
                embedding_calls=budget.embedding_calls, llm_calls=budget.llm_calls,
                token_usage=budget.tokens, elapsed_ms=int((time.monotonic()-started)*1000))
        cited, unknown = _marker_ids(answer.answer)
        valid = bool(cited) and not unknown and set(cited) <= set(source_map)
        valid = valid and _markers_are_supported(answer.answer, source_map, cited)
        trace.append(TraceEvent(
            step="citation_validation",
            summary=f"Validated {len(cited)} inline source markers" if valid else "Inline source markers failed validation",
            document_ids=[source_map[key].document.id for key in cited if key in source_map],
        ))
        if not valid:
            fallback_ids = cited if cited and set(cited) <= set(source_map) else list(source_map)[:2]
            fallback_map = {key: source_map[key] for key in fallback_ids}
            return ChatResult(**base, status="clarification_needed",
                content=_citation_fallback(fallback_map),
                citations=[_citation(item, as_of) for item in fallback_map.values()],
                trace=trace, embedding_calls=budget.embedding_calls, llm_calls=budget.llm_calls,
                token_usage=budget.tokens, elapsed_ms=int((time.monotonic()-started)*1000))
        citations = [_citation(source_map[key], as_of) for key in cited]
        claim = Claim(text=answer.answer, citation_ids=[c.id for c in citations], section="direct")
        content = answer.answer
        if answer.limitation:
            content += f"\n\nLưu ý: {answer.limitation}"
        if answer.clarification_question:
            content += f"\n\nĐể làm rõ hồ sơ: {answer.clarification_question}"
        trace.append(TraceEvent(step="generation", summary="Generated one source-marked answer",
                                document_ids=[c.document_id for c in citations]))
        return ChatResult(**base, status="answered", content=content, citations=citations,
            verified_claims=[claim], answer_sections=[AnswerSection(kind="direct", claim_indexes=[0])],
            trace=trace, embedding_calls=budget.embedding_calls, llm_calls=budget.llm_calls,
            token_usage=budget.tokens, elapsed_ms=int((time.monotonic()-started)*1000))
