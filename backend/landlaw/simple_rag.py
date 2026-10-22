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
from .conversation import classify


class SimpleAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)
    clarification_question: str = Field(default="", max_length=400)
    limitation: str = Field(default="", max_length=500)


# Vietnamese follow-up openers that refer back to the previous question. Only an
# explicit reference inherits context, so an unrelated new topic stays standalone.
FOLLOW_UP = re.compile(
    r"^(?:vậy|vậy thì|vậy nếu|thế|thế thì|thế nào|và|còn|như vậy|nếu vậy|trường hợp (?:đó|này)|"
    r"cái (?:đó|này)|điều (?:đó|này)|vấn đề (?:đó|này)|thì sao)", re.I)
SOURCE_MARKER = re.compile(r"[\[【]\s*S(\d+)\s*[\]】]", re.I)
WORD = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
STOP_WORDS = {
    "của", "cho", "được", "không", "nhà", "nước", "người", "đất", "khi",
    "theo", "với", "và", "hoặc", "này", "đó", "những", "một", "các",
    "trong", "đến", "từ", "về", "có", "là", "thì", "nếu", "phải",
}


def _review_notice(meta: dict) -> str:
    """State the review date of a standing snapshot without claiming legal currency."""
    reviewed = meta.get("reviewed_at")
    if not reviewed:
        return ""
    try:
        stamp = date.fromisoformat(str(reviewed)[:10])
    except ValueError:
        return ""
    return (f"Nguồn được đối chiếu đến {stamp.day:02d}/{stamp.month:02d}/{stamp.year}. "
            "Nếu cần xác nhận hiệu lực mới nhất, hãy kiểm tra văn bản gốc.")


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
    """Require grounded support for each asserted statement, not every framing sentence."""
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
        start = span.end()
        # Only statements that assert a personal outcome or a specific amount need
        # lexical support. Conditional framing the prompt requires ("đây là câu trả
        # lời có điều kiện...") or repeated adjacent markers carry no claim of their
        # own; rejecting them made real grounded answers unpublishable.
        if not _asserts_specific_outcome(statement):
            continue
        if not (_support_tokens(statement) & _support_tokens(source_map[identifier].chunk.text)):
            return False
    return True


AMOUNT = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:tỷ|triệu|nghìn|đồng|ha|m2|m²|%)", re.I)
CONFIDENT = re.compile(r"(chắc chắn|luôn luôn|tất cả trường hợp|không thể không)", re.I)


def _asserts_specific_outcome(statement: str) -> bool:
    """True only for statements asserting an amount or an unconditional entitlement."""
    return bool(AMOUNT.search(statement) or CONFIDENT.search(statement))


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


def _retrieval_query(message: str, history) -> tuple[str, bool]:
    """Resolve a short follow-up against the last user question for retrieval.

    Generation still receives the literal question plus recent history; only the
    retrieval/embedding query is expanded so a reference such as "vậy nếu chưa
    có sổ đỏ?" keeps the legal subject. Never expands from a greeting or
    out-of-scope turn, and never changes source, applicability or citation rules.
    """
    if not FOLLOW_UP.search(message.strip()):
        return message, False
    previous = next((item.content.strip() for item in reversed(list(history or []))
                     if item.role == 'user'), '')
    if not previous or classify(previous).kind != "legal":
        return message, False
    return f"{previous[:600]} — {message.strip()}", True


class SimpleRAG:
    def __init__(self, store, provider):
        self.store, self.provider = store, provider

    async def run(self, request, emit, release_id=None):
        started = time.monotonic()
        budget = Budget()
        as_of = request.as_of or local_date()
        trace: list[TraceEvent] = []
        # Conversation intents are answered before any corpus read. This keeps
        # social turns independent of database/corpus availability.
        base = dict(
            as_of=as_of,
            trace_id=str(uuid.uuid4()),
            model=self.provider.settings.generation_model,
            embedding_model=self.provider.settings.embedding_model,
            mode="simple_rag",
        )
        intent = classify(request.message, request.history)
        if intent.kind != "legal":
            status = "clarification_needed" if intent.kind in {"out_of_scope", "ambiguous"} else "answered"
            return ChatResult(
                **base,
                status=status,
                content=intent.reply,
                trace=[TraceEvent(step="conversation",
                                  summary=f"{intent.reason} handled without retrieval")],
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        release = await asyncio.to_thread(self.store.release, release_id, True)
        publication = await asyncio.to_thread(
            self.store.publication, (release or {}).get("id")
        )
        base.update(public_status(release, publication))
        base.update(
            corpus_release=(release or {}).get("id"),
            embedding_model=(release or {}).get("embedding_model", self.provider.settings.embedding_model),
        )
        if not self.provider.configured:
            raise ProviderUnavailable("GROQ_API_KEY chưa được cấu hình; chưa thể sinh câu trả lời")
        retrieval_query, inherited = _retrieval_query(request.message, request.history)
        vector = await self.provider.embed(retrieval_query, query=True, budget=budget, release=release)
        evidence = await asyncio.to_thread(
            self.store.search, retrieval_query, vector, request.project, (release or {}).get("id"),
            self.provider.settings.embedding_model, as_of
        )
        gate = await asyncio.to_thread(self.store.source_gate, (release or {}).get("id"))
        review_meta = await asyncio.to_thread(self.store.source_review_metadata, release)
        base["source_context"] = {
            "as_of": str(as_of),
            "source_checked_at": (release or {}).get("checked_at"),
            "source_fresh": False,
            "source_review_mode": review_meta.get("mode"),
            "source_reviewed_at": review_meta.get("reviewed_at"),
        }
        if gate is not None:
            reviews = await asyncio.to_thread(
                self.store.scoped_source_reviews,
                release,
                [(item.document.id, item.chunk.id, item.chunk.checksum) for item in evidence],
                as_of,
            )
            evidence = [
                item for item in evidence
                if reviews.get(f"{item.document.id}:{item.chunk.id}") in {"fresh", "standing", "reviewed_window"}
            ]
        evidence = [
            item for item in evidence
            if applicability(item.document, as_of, item.chunk) in {"current", "provision_specific", "context"}
        ][:5]
        base["retrieved_chunk_ids"] = [item.chunk.id for item in evidence]
        base["evidence_chunk_ids"] = [item.chunk.id for item in evidence]
        trace.append(TraceEvent(step="retrieval", summary=f"Selected {len(evidence)} reviewed passages",
                                document_ids=[item.document.id for item in evidence]))
        if inherited:
            trace.append(TraceEvent(step="retrieval_query",
                                    summary="Follow-up reference resolved against the previous question for retrieval only"))
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
QUY TẮC DẪN NGUỒN BẮT BUỘC: mỗi câu có nội dung pháp lý phải kết thúc bằng mã nguồn tương ứng, ví dụ "…phải đủ điều kiện theo Điều 95 [S1]".
Chỉ dùng các mã xuất hiện trong CONTEXT; không tạo URL, điều luật hay mã nguồn mới; nếu không có nguồn cho một ý thì không gắn mã cho ý đó."""
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
        raw_markers = len(SOURCE_MARKER.findall(answer.answer))
        trace.append(TraceEvent(
            step="citation_validation",
            summary=(f"Validated {len(cited)} inline source markers" if valid else
                     f"Inline source markers failed validation: {raw_markers} raw markers, "
                     f"{len(cited)} usable ids, out_of_range={bool(unknown)}"),
            document_ids=[source_map[key].document.id for key in cited if key in source_map],
        ))
        if not valid:
            fallback_ids = cited if cited and set(cited) <= set(source_map) else list(source_map)[:2]
            fallback_map = {key: source_map[key] for key in fallback_ids}
            fallback = _citation_fallback(fallback_map)
            notice = _review_notice(review_meta)
            if notice:
                fallback += f"\n\n{notice}"
            return ChatResult(**base, status="clarification_needed",
                content=fallback,
                citations=[_citation(item, as_of) for item in fallback_map.values()],
                trace=trace, embedding_calls=budget.embedding_calls, llm_calls=budget.llm_calls,
                token_usage=budget.tokens, elapsed_ms=int((time.monotonic()-started)*1000))
        citations = [_citation(source_map[key], as_of) for key in cited]
        claim = Claim(text=answer.answer, citation_ids=[c.id for c in citations], section="direct")
        content = answer.answer
        notice = _review_notice(review_meta)
        if notice:
            content += f"\n\n{notice}"
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
