import asyncio
import re
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from .models import ChatRequest, ChatResult, Citation, Document, Draft, Evidence, TraceEvent
from .provider import Budget, BudgetExceeded, Gemini, ProviderUnavailable
from .security import local_date, normalize, redact, utcnow
from .store import RateLimited, Store
from .publication import public_status


class ToolCall(BaseModel):
    name: Literal["search_law", "open_article", "check_effectivity", "search_project", "normalize_place"]
    query: str = Field(default="", max_length=1000)
    document_id: str | None = Field(default=None, max_length=120)
    locator: str | None = Field(default=None, max_length=200)


class Plan(BaseModel):
    tools: list[ToolCall] = Field(default_factory=list, max_length=3)
    missing_facts: list[str] = Field(default_factory=list, max_length=6)
    out_of_scope: bool = False


class SupportingQuote(BaseModel):
    claim_index: int = Field(ge=0,le=9)
    citation_id: str = Field(max_length=160)
    quote: str = Field(min_length=20,max_length=1600)


class Verification(BaseModel):
    supported_claim_indexes: list[int] = Field(default_factory=list)
    supporting_quotes: list[SupportingQuote] = Field(default_factory=list,max_length=80)
    issues: list[str] = Field(default_factory=list, max_length=10)
    needs_more_evidence: bool = False
    followup_query: str = Field(default="", max_length=1000)


class State(TypedDict, total=False):
    request: ChatRequest
    budget: Budget
    emit: Any
    history: list[dict]
    release: dict | None
    as_of: date
    plan: Plan
    evidence: list[Evidence]
    trace: list[TraceEvent]
    draft: Draft
    verification: Verification
    rounds: int
    repairs: int
    retrieval_degraded: bool
    result: ChatResult
    tool_notes: list[dict]


def applicability(doc: Document, as_of: date, chunk=None):
    if doc.source_kind == "official_news":
        return "context"
    if not doc.applicability_verified:
        return "unverified"
    if chunk:
        for scope in doc.provision_validity:
            ends = scope.get('effective_to')
            if ends and as_of >= date.fromisoformat(ends) and 'bang gia' in normalize(scope.get('locator','')) and '[BẢNG / ĐƠN GIÁ' in chunk.text:
                return 'historical'
            numbers = re.findall(r"Điều\s+(\d+)", scope.get('locator',''),flags=re.IGNORECASE)
            if any(re.search(rf'^Điều {n}(?:\D|$)',chunk.locator) for n in numbers):
                starts, ends = scope.get('effective_from'), scope.get('effective_to')
                if (starts and date.fromisoformat(starts) <= as_of and doc.effective_from and as_of < doc.effective_from) or (ends and as_of >= date.fromisoformat(ends)):
                    return 'provision_specific'
    if doc.effective_from and as_of < doc.effective_from:
        return "future"
    if doc.effective_to and as_of >= doc.effective_to:
        return "historical"
    return "current"


def relation_chunks(doc, locator):
    """Open the cited article in an amendment/transition instead of its first pages."""
    numbers = re.findall(r"Điều\s+(\d+)", locator or "", flags=re.IGNORECASE)
    selected = [c for c in doc.chunks if any(re.search(rf"^Điều {n}(?:\D|$)", c.locator) for n in numbers)]
    return (selected or doc.chunks)[:3]


def resolve_places(aliases, query, as_of):
    query = normalize(query)
    candidates = []
    for item in aliases:
        for alias in item.get("aliases", []):
            match = re.search(r"(?<!\w)" + re.escape(normalize(alias)) + r"(?!\w)", query)
            if match:
                candidates.append((match.start(), match.end(), item))
    selected, occupied = [], []
    for start, end, item in sorted(candidates, key=lambda x: x[1]-x[0], reverse=True):
        if any(start < right and end > left for left, right in occupied):
            continue
        occupied.append((start, end))
        future = bool(item.get("valid_from") and str(as_of) < item["valid_from"])
        selected.append({**item, "normalization_status": "future_mapping" if future else "ambiguous" if item.get("ambiguous") else "verified",
                         "query_as_of": str(as_of)})
    return selected[:6]


class Agent:
    def __init__(self, store: Store, provider: Gemini):
        self.store, self.provider = store, provider
        graph = StateGraph(State)
        for name, node in [("plan", self.plan), ("tools", self.tools), ("synthesize", self.synthesize),
                           ("verify", self.verify), ("repair", self.repair), ("finish", self.finish)]:
            graph.add_node(name, node)
        graph.add_edge(START, "plan")
        graph.add_edge("plan", "tools")
        graph.add_edge("tools", "synthesize")
        graph.add_edge("synthesize", "verify")
        graph.add_conditional_edges("verify", self.route, {"retry": "tools", "repair":"repair", "finish": "finish"})
        graph.add_edge('repair','synthesize')
        graph.add_edge("finish", END)
        self.graph = graph.compile()

    async def event(self, state, step, summary, tool=None, docs=None):
        event = TraceEvent(step=step, tool=tool, summary=summary, document_ids=docs or [],
                           elapsed_ms=int((time.monotonic()-state["budget"].started)*1000))
        state["trace"].append(event)
        await state["emit"](event)

    async def plan(self, state):
        request = state["request"]
        if request.mode == "baseline":
            prior = next((m['content'] for m in reversed(state['history']) if m['role']=='user'), '')
            # Baseline also receives the same conversational context; no planner call.
            query = (prior[:500]+' '+request.message) if prior else request.message
            state["plan"] = Plan(tools=[ToolCall(name="search_law", query=query[:1000])])
        else:
            state["plan"] = await self.provider.generate(Plan,
                "Chọn tối đa 3 công cụ chỉ đọc để lấy chứng cứ. search_law tìm luật; search_project tìm hồ sơ dự án; "
                "check_effectivity kiểm tra văn bản theo document_id đã biết; open_article mở điều khoản đã biết; "
                "normalize_place tìm tên địa bàn theo danh mục. Với câu hỏi quyền lợi cá nhân, liệt kê dữ kiện thiếu. "
                "Chỉ đánh dấu out_of_scope khi không liên quan đất đai/quy hoạch Hà Nội. "
                "Không đoán document_id; khi chưa biết dùng search_law.",
                {"question": redact(request.message), "project": request.project, "as_of": str(state["as_of"]),
                 "history": state["history"], "catalogue": self.catalogue(state["release"])}, state["budget"])
        await self.event(state, "plan", f"Đã chọn {len(state['plan'].tools)} công cụ; chế độ {request.mode}.")
        return state

    @staticmethod
    def catalogue(release):
        return [{"id": d["id"], "title": d["title"], "project": d.get("project"),
                 'effective_from':d.get('effective_from'),'effective_to':d.get('effective_to')}
                for d in (release or {}).get("documents", [])][:100]

    async def search(self, state, query, project=None):
        vector = None
        try:
            vector = await self.provider.embed(query, query=True,budget=state['budget'],release=state['release'])
        except (ProviderUnavailable, RateLimited):
            state['retrieval_degraded']=True
            await self.event(state, "retrieval", "Embedding chưa khả dụng; dùng tìm kiếm từ khóa trong lượt này.")
        return await asyncio.to_thread(self.store.search, query, vector, project,
                                       (state["release"] or {}).get("id"), (state['release'] or {}).get('embedding_model', self.provider.settings.embedding_model))

    async def tools(self, state):
        if state["plan"].out_of_scope or not state["release"]:
            return state
        if state["rounds"]:
            calls = [ToolCall(name="search_law", query=state["verification"].followup_query or state["request"].message)]
        else:
            calls = state["plan"].tools or [ToolCall(name="search_law", query=state["request"].message)]
        release_id = state["release"]["id"]
        found = {e.chunk.id: e for e in state["evidence"]}
        for call in calls:
            state["budget"].tool()
            results = []
            if call.name in {"search_law", "search_project"}:
                results = await self.search(state, call.query or state["request"].message, state["request"].project)
            elif call.name in {"open_article", "check_effectivity"} and call.document_id:
                doc = await asyncio.to_thread(self.store.open_document, call.document_id, release_id, call.locator)
                if doc:
                    results = [Evidence(chunk=c, document=doc) for c in doc.chunks
                               if not call.locator or normalize(call.locator) in normalize(c.locator)][:3]
            elif call.name == "normalize_place":
                aliases = state["release"].get("place_aliases", [])
                matched = resolve_places(aliases, call.query or state["request"].message, state["as_of"])
                state["tool_notes"].append({"tool": call.name, "matches": matched[:6]})
                await self.event(state, "tool", f"Tìm thấy {len(matched)} ánh xạ địa bàn có nguồn; thiếu ánh xạ thì cần hỏi lại.", call.name)
            for item in results:
                item.applicability = applicability(item.document, state["as_of"],item.chunk)
                found[item.chunk.id] = item
            await self.event(state, "tool", f"Thu được {len(results)} đoạn chứng cứ.", call.name,
                             sorted({e.document.id for e in results}))
        # Follow legal relationships; deterministic scope checks are never delegated entirely to the LLM.
        for doc_id in list(dict.fromkeys(e.document.id for e in found.values()))[:4]:
            if state["budget"].tool_calls >= 12:
                break
            state["budget"].tool()
            relations = await asyncio.to_thread(self.store.relations, doc_id, release_id)
            for relation in relations:
                related_id = relation.source_id if relation.target_id == doc_id else relation.target_id
                locator = (relation.source_locator or relation.locator) if related_id == relation.source_id else " ".join(relation.target_locators)
                doc = await asyncio.to_thread(self.store.open_document, related_id, release_id, locator)
                if doc:
                    for chunk in relation_chunks(doc, locator):
                        found.setdefault(chunk.id, Evidence(chunk=chunk, document=doc,
                                                           applicability=applicability(doc, state["as_of"],chunk)))
            await self.event(state, "applicability", f"Đã kiểm tra {len(relations)} quan hệ pháp lý theo thời điểm.", "check_effectivity", [doc_id])
        # Keep existing hits stable and add parent text, capped to a bounded context.
        for item in list(found.values())[:8]:
            if item.chunk.parent_id:
                parent = await asyncio.to_thread(self.store.chunk, item.chunk.parent_id, release_id)
                if parent:
                    found.setdefault(parent.id, Evidence(chunk=parent, document=item.document, applicability=item.applicability))
        state["evidence"] = list(found.values())[:16]
        state["rounds"] += 1
        return state

    def context(self, state):
        return [{"citation_id": e.chunk.id, "document_id": e.document.id, "title": e.document.title,
                 "kind": e.document.source_kind, "locator": e.chunk.locator, "text": e.chunk.text,
                 "applicability": e.applicability, "effective_from": str(e.document.effective_from),
                 "effective_to": str(e.document.effective_to),
                 "provision_validity": e.document.provision_validity,
                 "legal_relations": self.relation_context(e, state)} for e in state["evidence"]]

    def relation_context(self, evidence, state):
        docs = {d["id"]: d for d in (state["release"] or {}).get("documents", [])}
        result = []
        for relation in (state["release"] or {}).get("relations", []):
            if evidence.document.id not in {relation["source_id"], relation["target_id"]}:
                continue
            source = docs.get(relation["source_id"])
            result.append({**relation, "source_effective_from": (source or {}).get("effective_from"),
                           "source_verified": (source or {}).get("applicability_verified", False),
                           "scope_note": "Phạm vi từng điều khoản; không suy ra toàn văn bị bãi bỏ từ quan hệ sửa đổi/bãi bỏ một phần."})
        return result

    async def synthesize(self, state):
        if state["plan"].out_of_scope:
            state["draft"] = Draft(status="insufficient_evidence", summary="Câu hỏi nằm ngoài phạm vi đất đai và quy hoạch Hà Nội.")
        elif not state["evidence"]:
            state["draft"] = Draft(status="insufficient_evidence", summary="Chưa tìm được chứng cứ trong bộ dữ liệu đã công bố.",
                                   missing_facts=state["plan"].missing_facts)
        else:
            state["draft"] = await self.provider.generate(Draft,
                "Tạo câu trả lời có cấu trúc. summary chỉ giới thiệu kết quả và giới hạn, không chứa kết luận pháp lý "
                "không dẫn nguồn. MỌI kết luận pháp lý nằm trong claims, gắn citation_ids có trong evidence. "
                "Đoạn unverified/future không chứng minh quy định hiện hành. historical chỉ dùng khi giải thích lịch sử "
                "provision_specific có mốc riêng tại khoản được ghi; phải kiểm tra đúng khoản và không suy hiệu lực toàn điều. "
                "hoặc chuyển tiếp được chứng minh. Không coi official_news là quy phạm. Nếu thiếu dữ kiện hồ sơ, "
                "dùng clarification_needed. Không kết luận chắc chắn về quyền lợi hộ/thửa hoặc số tiền. "
                "next_steps chỉ là hướng dẫn đối chiếu hồ sơ chung; thời hạn/điều kiện pháp lý phải đưa vào claims có nguồn. "
                "coverage_gaps và unresolved_relations chỉ mô tả phần còn thiếu, không phải chứng cứ. "
                "Không khẳng định quyền lợi lịch sử theo QĐ56/2024 khi thiếu toàn văn; không suy nội dung văn bản cũ "
                "từ văn bản thay thế. Khi câu hỏi phụ thuộc phần thiếu, trả lời có giới hạn và chỉ rõ tài liệu cần đối chiếu. "
                "Giữ đúng chủ thể: Chủ tịch UBND khác UBND; không rút gọn làm đổi thẩm quyền. "
                "kind=applicability chỉ để nêu mốc hiệu lực/tình trạng áp dụng, không chứa quyền lợi. "
                "Có thể dẫn đoạn future để giải thích văn bản CHƯA có hiệu lực, không áp dụng quyền lợi từ đó. "
                "kind=context chỉ cho bối cảnh dự án. Trả lời trực tiếp vấn đề được hỏi trước khi giải thích bổ sung.",
                {"question": redact(state["request"].message), "as_of": str(state["as_of"]), "history": state["history"],
                 "missing_facts": state["plan"].missing_facts, "tool_results": state["tool_notes"], "evidence": self.context(state),
                 "coverage_gaps": (state['release'] or {}).get('coverage_gaps', []),
                 "unresolved_relations": (state['release'] or {}).get('unresolved_relations', []),
                 "previous_issues": state.get("verification", Verification()).issues}, state["budget"])
        await self.event(state, "synthesis", "Đã tạo bản trả lời; đang kiểm tra trước khi hiển thị.")
        return state

    async def verify(self, state):
        draft = state["draft"]
        if not state["evidence"]:
            state["verification"] = Verification()
            return state
        evidence = {e.chunk.id: e for e in state["evidence"]}
        structural_issues = []
        for index, claim in enumerate(draft.claims):
            if any(i not in evidence for i in claim.citation_ids):
                structural_issues.append(f"Claim {index}: ID trích dẫn không có trong chứng cứ")
            if all(i in evidence and (evidence[i].applicability=='unverified' or
                   (evidence[i].applicability=='future' and claim.kind!='applicability')) for i in claim.citation_ids):
                structural_issues.append(f"Claim {index}: căn cứ chưa xác minh tính áp dụng")
            normalized_claim=normalize(claim.text)
            if 'chuyen giao cho uy ban nhan dan cap xa' in normalized_claim:
                if any('chuyen giao cho chu tich uy ban nhan dan cap xa' in normalize(evidence[i].chunk.text)
                       for i in claim.citation_ids if i in evidence):
                    structural_issues.append(f'Claim {index}: nhầm Chủ tịch UBND cấp xã với UBND cấp xã')
            # A current assertion from an affected original article must also cite the effective amendment.
            # Clause-level changes never invalidate the whole original document.
            cited_documents = {evidence[i].document.id for i in claim.citation_ids if i in evidence}
            for relation in (state['release'] or {}).get('unresolved_relations', []):
                if relation['target_id'] in cited_documents and relation['type'] in {'amends','repeals'}:
                    structural_issues.append(f"Claim {index}: thiếu văn bản tác động để xác minh phạm vi điều khoản")
            for citation_id in claim.citation_ids:
                if citation_id not in evidence or evidence[citation_id].applicability != "current":
                    continue
                item = evidence[citation_id]
                for relation in self.relation_context(item, state):
                    if relation["target_id"] != item.document.id or relation["type"] not in {"amends", "repeals"}:
                        continue
                    starts = relation.get("source_effective_from")
                    if not starts or date.fromisoformat(starts) > state["as_of"]:
                        continue
                    affected_articles = [n for locator in relation.get("target_locators", [])
                                         for n in re.findall(r"Điều\s+(\d+)", locator, flags=re.IGNORECASE)]
                    affected = not relation.get('target_locators_complete') or any(re.search(rf"^Điều {n}(?:\D|$)", item.chunk.locator) for n in affected_articles)
                    if affected and relation["source_id"] not in cited_documents:
                        structural_issues.append(f"Claim {index}: điều khoản có sửa đổi/bãi bỏ một phần; cần dẫn cả văn bản tác động")
        checked = await self.provider.generate(Verification,
            "Đối chiếu từng claim với đúng đoạn trích và thời điểm. Chỉ đưa index vào supported_claim_indexes nếu "
            "chứng cứ hỗ trợ đầy đủ nội dung, phạm vi và tính áp dụng. Kiểm tra summary và next_steps: nếu có kết luận "
            "pháp lý chưa dẫn nguồn, ghi issues. Không xác nhận current từ đoạn unverified. historical chỉ hỗ trợ câu "
            "về quá khứ hoặc điều khoản chuyển tiếp có chứng cứ. Nguồn tin chỉ hỗ trợ sự kiện/bối cảnh, không quyền lợi. "
            "Đặt needs_more_evidence và followup_query khi một lượt truy xuất bổ sung có thể khắc phục. "
            "provision_specific phải đối chiếu đúng khoản có mốc riêng; không suy hiệu lực toàn điều. Không tự tạo thêm chứng cứ. "
            "Kiểm tra chính xác chủ thể, đặc biệt Chủ tịch UBND khác UBND; không xác nhận phép rút gọn đổi thẩm quyền. "
            "kind=applicability có thể dùng future để nói CHƯA có hiệu lực và nêu ngày bắt đầu đã xác minh; "
            "không cho phép quyền lợi/nghĩa vụ hiện tại từ future. Trích dẫn phải hỗ trợ chính nội dung claim, "
            "không chỉ cùng tên hoặc số hiệu văn bản. Với MỖI citation_id của MỖI claim được hỗ trợ, "
            "trả supporting_quotes gồm claim_index, citation_id, quote sao chép nguyên văn từ text của chính citation đó. "
            "Quote phải chứng minh nội dung claim tương ứng; đoạn mở đầu/căn cứ tên văn bản không chứng minh điều khoản ở trang khác. "
            "Không có quote chứng minh thì bỏ index và yêu cầu truy xuất bổ sung. Nếu đáp án bỏ sót câu hỏi trực tiếp, ghi issues để sửa.",
            {"question": redact(state["request"].message), "as_of": str(state["as_of"]),
             "draft": draft.model_dump(), "evidence": self.context(state),
             "coverage_gaps": (state['release'] or {}).get('coverage_gaps', []),
             "unresolved_relations": (state['release'] or {}).get('unresolved_relations', [])}, state["budget"])
        checked.issues = structural_issues + checked.issues
        for index,claim in enumerate(draft.claims):
            proven = {q.citation_id for q in checked.supporting_quotes if q.claim_index==index
                and q.citation_id in evidence and normalize(q.quote) in normalize(evidence[q.citation_id].chunk.text)}
            if set(claim.citation_ids)-proven:
                checked.issues.append(f'Claim {index}: thiếu trích đoạn nguyên văn chứng minh tại đúng citation_id')
                structural_issues.append(f'Claim {index}: thiếu chứng cứ trích dẫn trực tiếp')
        blocked = {int(match.group(1)) for issue in structural_issues if (match := re.match(r"Claim (\d+):", issue))}
        allowed = {i for i in range(len(draft.claims)) if all(c in evidence for c in draft.claims[i].citation_ids)
                   and i not in blocked and not all(evidence[c].applicability=='unverified' or
                   (evidence[c].applicability=='future' and draft.claims[i].kind!='applicability') for c in draft.claims[i].citation_ids)}
        checked.supported_claim_indexes = sorted(set(checked.supported_claim_indexes) & allowed)
        state["verification"] = checked
        await self.event(state, "verification", f"{len(checked.supported_claim_indexes)}/{len(draft.claims)} kết luận được hỗ trợ; {len(checked.issues)} vấn đề.")
        return state

    @staticmethod
    def route(state):
        verification = state["verification"]
        can_retry = state["request"].mode == "agentic" and state["rounds"] < 2 and state["budget"].llm_calls <= 4
        if can_retry and verification.needs_more_evidence:
            return "retry"
        incomplete = len(verification.supported_claim_indexes) < len(state['draft'].claims)
        if (verification.issues or incomplete) and state.get('repairs',0)<1 and state['budget'].llm_calls<=4:
            return 'repair'
        return "finish"

    async def repair(self,state):
        state['repairs']=state.get('repairs',0)+1
        await self.event(state,'repair','Đang sửa một lần theo các lỗi kiểm chứng trên cùng chứng cứ.')
        return state

    async def finish(self, state):
        draft, check = state["draft"], state["verification"]
        supported = set(check.supported_claim_indexes)
        claims = [c for i, c in enumerate(draft.claims) if i in supported]
        evidence = {e.chunk.id: e for e in state["evidence"]}
        for index,claim in enumerate(claims):
            if claim.kind=='applicability' and all(evidence[i].applicability=='future' for i in claim.citation_ids):
                claims[index]=claim.model_copy(update={'text':claim.text+f" Văn bản này chưa có hiệu lực tại ngày {state['as_of'].strftime('%d/%m/%Y')}."})
        cited_ids = list(dict.fromkeys(i for c in claims for i in c.citation_ids))
        citations = [Citation(id=i, document_id=evidence[i].document.id, title=evidence[i].document.title,
                              document_number=evidence[i].document.document_number, url=str(evidence[i].document.url),
                              locator=evidence[i].chunk.locator, excerpt=evidence[i].chunk.text[:1600],
                              checked_at=evidence[i].document.checked_at, applicability=evidence[i].applicability) for i in cited_ids]
        status = draft.status
        if draft.claims and (len(claims) != len(draft.claims) or check.issues):
            status = "insufficient_evidence"
        if status == "answered" and not claims:
            status = "insufficient_evidence"
        release = state["release"]
        stale = False
        if release:
            checked_at = datetime.fromisoformat(release["checked_at"].replace("Z", "+00:00"))
            stale = utcnow() - checked_at > timedelta(days=7)
        if stale and state["as_of"] >= local_date():
            status = "insufficient_evidence"
            claims, citations = [], []
        # Only verified content is rendered. Never pass unchecked summary/next_steps on a failed verification.
        # Summary prose is never treated as an unchecked place to smuggle legal assertions.
        intro = {"answered": "Đã đối chiếu các căn cứ dưới đây.",
                 "clarification_needed": "Cần bổ sung dữ kiện để xác định quy định áp dụng cho hồ sơ cụ thể.",
                 "insufficient_evidence": "Chưa có đủ chứng cứ đã xác minh để kết luận đầy đủ."}[status]
        if stale and state["as_of"] >= local_date():
            intro = "Bộ dữ liệu đã quá bảy ngày chưa được kiểm tra nguồn; chưa thể xác nhận quy định hiện hành."
        content = intro
        if claims:
            content += "\n\n" + "\n\n".join(c.text + " " + " ".join(f"[{cited_ids.index(i)+1}]" for i in c.citation_ids) for c in claims)
        missing = list(dict.fromkeys(state["plan"].missing_facts + draft.missing_facts))
        if missing and status == "answered":
            status = "clarification_needed"
            content = content.replace("Đã đối chiếu các căn cứ dưới đây.", "Cần bổ sung dữ kiện để xác định quy định áp dụng cho hồ sơ cụ thể.", 1)
        if missing:
            content += "\n\nThông tin cần bổ sung:\n" + "\n".join(f"- {x}" for x in missing)
        historical_question = state['as_of'] < date(2026,4,2) and any(number in normalize(state['request'].message)
            for number in ('40/2026','56/2024','boi thuong'))
        if historical_question and any(g['document_id']=='qd-56-2024-hanoi' for g in (release or {}).get('coverage_gaps',[])):
            content+='\n\nBộ dữ liệu chưa có toàn văn đạt kiểm tra của QĐ56/2024; chưa thể xác định đầy đủ quyền lợi hồ sơ lịch sử phụ thuộc văn bản này.'
        if draft.next_steps and not check.issues:
            content += "\n\nBước tiếp theo:\n" + "\n".join(f"- {x}" for x in draft.next_steps)
        content += f"\n\nThời điểm xem xét: {state['as_of'].strftime('%d/%m/%Y')}."
        if release:
            content += f" Dữ liệu được kiểm tra: {release['checked_at'][:10]}."
        budget = state["budget"]
        state["result"] = ChatResult(status=status, content=content, citations=citations, verified_claims=claims, as_of=state["as_of"],
            corpus_release=(release or {}).get("id"), trace_id=str(uuid.uuid4()), trace=state["trace"], missing_facts=missing,
            llm_calls=budget.llm_calls, tool_calls=budget.tool_calls, token_usage=budget.tokens,
            embedding_calls=budget.embedding_calls,
            elapsed_ms=int((time.monotonic()-budget.started)*1000), model=self.provider.settings.gemini_model,
            embedding_model=(state['release'] or {}).get('embedding_model', self.provider.settings.embedding_model), mode=state["request"].mode,
            support_level="full" if status == "answered" else "partial" if citations else "insufficient",
            retrieved_chunk_ids=[e.chunk.id for e in state["evidence"][:8]],
            evidence_chunk_ids=[e.chunk.id for e in state["evidence"]])
        publication = await asyncio.to_thread(self.store.publication, (release or {}).get('id'))
        state['result'] = state['result'].model_copy(update=public_status(release, publication))
        if state.get('retrieval_degraded'):
            state['result']=state['result'].model_copy(update={'retrieval_mode':'lexical_fallback'})
        return state

    async def run(self, request, emit, release_id=None):
        budget = Budget()
        state: State = {"request": request, "budget": budget, "emit": emit, "trace": [], "evidence": [], "rounds": 0, "tool_notes": [],
                        "as_of": request.as_of or local_date(), "release": None, "history": [], 'repairs':0}
        try:
            if not self.provider.configured:
                raise ProviderUnavailable("GEMINI_API_KEY chưa được cấu hình; không sinh câu trả lời giả")
            async with asyncio.timeout(self.provider.settings.turn_timeout_seconds):
                state["release"] = await asyncio.to_thread(self.store.release, release_id, True)
                history = await asyncio.to_thread(self.store.messages, request.session_id, 8)
                # Only displayed text, never traces/model-internal state, enters subsequent prompts.
                state["history"] = [{"role": m["role"], "content": redact(m["payload"].get("content", "")[:3000]),
                    "as_of": m['payload'].get('as_of'), 'citations': [{k:c.get(k) for k in ('document_id','document_number','locator')}
                        for c in m['payload'].get('citations',[])[:8]]} for m in history]
                output = await self.graph.ainvoke(state, config={"recursion_limit": 16})
                return output["result"]
        except (ProviderUnavailable, RateLimited, BudgetExceeded, TimeoutError) as exc:
            status = "limited" if isinstance(exc, (RateLimited, BudgetExceeded)) else "error"
            content = "Đã hết giới hạn miễn phí hoặc ngân sách của lượt hỏi. Vui lòng thử lại sau." if status == "limited" else (
                "Lượt hỏi đã quá thời gian xử lý. Vui lòng thử lại." if isinstance(exc, TimeoutError) else str(exc))
            publication = await asyncio.to_thread(self.store.publication, (state['release'] or {}).get('id'))
            return ChatResult(**public_status(state['release'], publication), status=status, content=content, as_of=state["as_of"],
                corpus_release=(state["release"] or {}).get("id"), trace_id=str(uuid.uuid4()), trace=state["trace"],
                llm_calls=budget.llm_calls, tool_calls=budget.tool_calls, token_usage=budget.tokens,
                embedding_calls=budget.embedding_calls,
                elapsed_ms=int((time.monotonic()-budget.started)*1000), model=self.provider.settings.gemini_model,
                embedding_model=(state['release'] or {}).get('embedding_model', self.provider.settings.embedding_model), mode=request.mode,
                retry_after=exc.retry_after if isinstance(exc, RateLimited) else None)
