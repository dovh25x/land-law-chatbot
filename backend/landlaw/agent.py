import asyncio
import json
import re
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from .models import ChatRequest, ChatResult, Citation, Claim, Document, Draft, Evidence, Relation, TraceEvent
from .provider import Budget, BudgetExceeded, GroqProvider, ProviderUnavailable
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


class SupportingSpan(BaseModel):
    claim_index: int = Field(ge=0,le=9)
    citation_id: str = Field(max_length=160)
    span_id: str = Field(max_length=220)


class Verification(BaseModel):
    supported_claim_indexes: list[int] = Field(default_factory=list)
    supporting_quotes: list[SupportingQuote] = Field(default_factory=list,max_length=80)
    supporting_spans: list[SupportingSpan] = Field(default_factory=list,max_length=80)
    issues: list[str] = Field(default_factory=list, max_length=10)
    needs_more_evidence: bool = False
    followup_query: str = Field(default="", max_length=1000)


class State(TypedDict, total=False):
    unsupported_project: bool
    unsupported_references: list[str]
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
    source_fact_id: str | None
    source_fact_type: str | None
    private_entitlement_check: bool
    freshness_question: bool
    place_clarification: bool
    general_rule_question: bool
    opened_relations: set


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
            numbers = re.findall(r"Điều\s+(\d+[a-z]?)", scope.get('locator',''),flags=re.IGNORECASE)
            if any(re.search(rf'^Điều {n}(?:\s|$)',chunk.locator,re.IGNORECASE) for n in numbers):
                starts, ends = scope.get('effective_from'), scope.get('effective_to')
                if (starts and doc.effective_from and date.fromisoformat(starts) != doc.effective_from) or (ends and as_of >= date.fromisoformat(ends)):
                    return 'provision_specific'
    if doc.effective_from and as_of < doc.effective_from:
        return "future"
    if doc.effective_to and as_of >= doc.effective_to:
        return "historical"
    return "current"


def relation_chunks(doc, locator):
    """Open the cited article in an amendment/transition instead of its first pages."""
    numbers = re.findall(r"Điều\s+(\d+[a-z]?)", locator or "", flags=re.IGNORECASE)
    selected = [c for c in doc.chunks if any(re.search(rf"^Điều {n}(?:\s|$)", c.locator,re.IGNORECASE) for n in numbers)]
    return (selected or doc.chunks)[:3]


def citation_source_url(item):
    """Link a physical page only when its exact source attachment is known."""
    prefix = item.document.id + '-'
    if not item.chunk.id.startswith(prefix) or not item.chunk.page:
        return None
    index = item.chunk.id[len(prefix):].split('-', 1)[0]
    if not index.isdigit():
        return None
    for source in item.document.source_pages:
        if source.page_index == int(index):
            return str(source.url)
    for source in item.document.source_files:
        if source.first_page_index <= int(index) <= source.last_page_index:
            return str(source.url).split('#')[0] + f'#page={item.chunk.page}'
    return None


def relation_may_affect(relation, doc_id, passages):
    """Skip only a verified complete amendment scope outside retrieved articles."""
    if (relation.target_id != doc_id or relation.type not in {'amends', 'repeals'}
            or not relation.target_locators_complete):
        return True
    articles = {n.lower() for locator in relation.target_locators
                for n in re.findall(r'Điều\s+(\d+[a-z]?)', locator, re.IGNORECASE)}
    if not articles:
        return True
    return any(p.document.id == doc_id and any(
        re.search(rf'^Điều {n}(?:\s|$)', p.chunk.locator, re.IGNORECASE) for n in articles) for p in passages)


def amendment_affects_claim(relation, item, claim):
    """Exclude only proven different clauses in a complete amendment scope.

    An eligibility cross-reference alone is not the claim's legal basis. Require
    an explicit clause+article attribution matching the cited article. Unknown
    or whole-article scopes remain conservative.
    """
    if not relation.get('target_locators_complete'):return True
    article=re.match(r'^Điều (\d+[a-z]?)\b',item.chunk.locator,re.I)
    if not article:return True
    basis=set(re.findall(r'\bkhoan\s+(\d+)\s+dieu\s+'+re.escape(article[1])+r'\b',normalize(claim.text)))
    if not basis:return True
    targets=[normalize(loc) for loc in relation.get('target_locators',[])
             if re.search(r'\bdieu\s+'+re.escape(article[1])+r'\b',normalize(loc))]
    if not targets:return False
    if any(not re.search(r'\bkhoan\s+\d+\b',t) for t in targets):return True
    affected={n for t in targets for n in re.findall(r'\bkhoan\s+(\d+)\b',t)}
    return bool(basis & affected)


def dates_in(text):
    text = normalize(text)
    values = set()
    for pattern in (r'(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?!\d)',
                    r'ngay\s+(\d{1,2})\s+thang\s+(\d{1,2})\s+nam\s+(\d{4})'):
        for day, month, year in re.findall(pattern, text):
            try:
                values.add(date(int(year), int(month), int(day)))
            except ValueError:
                pass
    return values


def quote_matches(quote, text):
    """Accept exact text or explicitly omitted, ordered verbatim spans.

    Legal quotations often omit the list between an article's subject and point
    (d). Every retained span must still occur in this same cited passage.
    """
    quote,text=normalize(quote),normalize(text)
    if quote in text:
        return True
    spans=re.split(r'\s*(?:\[\.\.\.\]|\[…\]|\.\.\.|…)\s*',quote)
    if not 2<=len(spans)<=4 or any(len(span)<20 for span in spans):
        return False
    start=0
    for span in spans:
        position=text.find(span,start)
        if position<0:
            return False
        start=position+len(span)
    return True


def clause_attribution_issues(claim, evidence):
    """Reject literal list examples attributed to a different numbered clause.

    This is a narrow structural check, not a legal entailment classifier. Only
    explicit clause/article attributions and unambiguous source list prefixes
    are compared; the semantic verifier still checks the whole proposition.
    """
    issues = []
    for sentence in re.split(r'[.;\n]', normalize(claim.text)):
        references = set(re.findall(r'\bkhoan\s+(\d+)\s+dieu\s+(\d+[a-z]?)\b', sentence))
        if len(references) != 1:
            continue
        clause, article = next(iter(references))
        blocks = {}
        cited_documents = {e.document.id for e in evidence if e.chunk.id in claim.citation_ids}
        for item in evidence:
            if item.document.id not in cited_documents:
                continue
            if not re.match(rf'^dieu {article}(?:\s|$)', normalize(item.chunk.locator)):
                continue
            text = normalize(item.chunk.text)
            matches = list(re.finditer(r'(?<![\d/])\b(\d+)\.\s+', text))
            for index, match in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                blocks.setdefault(match[1], []).append(text[match.end():end])
        target = ' '.join(blocks.get(clause, []))
        if not target:
            continue
        for number, texts in blocks.items():
            if number == clause:
                continue
            for body in texts:
                for point in re.split(r'\b[a-zđ]\)\s+', body)[1:]:
                    prefix = ' '.join(re.findall(r'\w+', point)[:4])
                    if len(prefix.split()) == 4 and prefix in sentence and prefix not in target:
                        issues.append(f'Nội dung ví dụ thuộc khoản {number}, không chứng minh điều kiện tại khoản {clause} Điều {article}')
    return list(dict.fromkeys(issues))


def claim_source_dates(text, as_of):
    """A question's observation date is not a statutory commencement date."""
    values=dates_in(text)
    normalized=normalize(text)
    starts=[match[0] for match in re.finditer(r'co hieu luc(?:\s+thi hanh)?\s+(?:ke tu|tu|ngay)[^.;\n]{0,80}',normalized)]
    if any(phrase in normalized for phrase in ('tai ngay','vao ngay','den ngay')) and not any(as_of in dates_in(s) for s in starts):
        values.discard(as_of)
    return values


def source_effective_dates(text):
    """Read dates in a commencement clause, excluding dates of replaced acts."""
    result=set()
    for match in re.finditer(r'co hieu luc(?:\s+thi hanh)?\b[^.;\n]{0,160}',normalize(text)):
        result.update(dates_in(match[0].split(' va ')[0]))
    return result


def claim_effective_dates(text, as_of=None):
    """Commencement/expiry dates, excluding an act's separately stated issue date."""
    pattern = (r'hieu luc(?:\s+thi hanh)?\s+(?:(?:ke tu|tu|vao|den)\s+)?(?:ngay\s+)?'
               r'(\d{1,2}(?:[/-]\d{1,2}[/-]\d{4}|\s+thang\s+\d{1,2}\s+nam\s+\d{4}))')
    normalized=normalize(text)
    values=set()
    for match in re.finditer(pattern,normalized):
        observed_status=bool(as_of and 'vao' in match[0] and re.search(
            r'(?:(?:khong|chua)\s+(?:con|co)|van\s+con|con)\s+$',normalized[:match.start()]))
        for value in dates_in('ngay '+match[1]):
            if not (observed_status and value==as_of):values.add(value)
    return values


def public_missing_facts(facts,release):
    known=['/'.join(normalize(d.get('document_number') or '').split('/')[:2])
        for d in (release or {}).get('documents',[]) if d.get('issued_on')]
    return list(dict.fromkeys(fact for fact in facts
        if not any(key in fact.lower() for key in ('document_id','citation_id'))
        and not ('ngay ban hanh' in normalize(fact)
            and any(number and number in normalize(fact) for number in known))))


def private_entitlement_check(question):
    """A personal guarantee needs file evidence, not a law-search result.

    General questions about eligibility remain legal queries. This guard only
    catches a request to confirm the questioner's own entitlement or amount.
    """
    text=normalize(question)
    personal=bool(re.search(r'\b(?:nha|dat|ho so|gia dinh|ho gia dinh|thua dat)\s+(?:cua\s+)?(?:toi|minh)\b',text))
    certainty=any(word in text for word in ('chac chan','co chac','khang dinh','bao nhieu tien','bao nhieu dong','dung khong'))
    entitlement=any(word in text for word in ('boi thuong','tai dinh cu','quyen loi','duoc ho tro'))
    return personal and certainty and entitlement


def source_spans(evidence):
    """Number exact overlapping source passages; the model cannot supply their text."""
    result={}
    for item in evidence:
        text=item.chunk.text
        for start in range(0,len(text),1200):
            quote=text[start:start+1400]
            if len(quote)<20:continue
            key=f'{item.chunk.id}:span:{start}'
            result[key]={'span_id':key,'citation_id':item.chunk.id,'quote':quote}
    return result


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
    def __init__(self, store: Store, provider: GroqProvider):
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
        question=normalize(request.message)
        contextual_query=request.message
        if not re.search(r'\d{1,6}/(?:19|20)\d{2}',question) and any(
                phrase in question for phrase in ('van ban do','van ban vua neu','van ban thay the vua neu','quyet dinh nay')):
            last=next((m for m in reversed(state['history']) if m['role']=='assistant'),{})
            cited={c.get('document_id') for c in last.get('citations',[]) if c.get('document_id')}
            known={d['id']:d for d in (state['release'] or {}).get('documents',[])}
            if len(cited)==1 and next(iter(cited)) in known:
                number=known[next(iter(cited))].get('document_number')
                if number:contextual_query=f'{number}: {request.message}'
        literal_numbers=set(re.findall(r'(?<![\d/])\d{1,6}/(?:19|20)\d{2}(?!/\d)',question))
        known_numbers={'/'.join(normalize(d.get('document_number') or '').split('/')[:2])
                       for d in (state['release'] or {}).get('documents',[])}
        direct_effectivity=(1<=len(literal_numbers)<=2 and literal_numbers<=known_numbers
            and any(term in question for term in ('hieu luc','van ban nao thay the','kiem tra mau thuan','bai bo'))
            and not any(term in question for term in ('ho so','quyen loi','tinh tien','tinh boi thuong')))
        future_date_question=('ap dung ngay' in question and len(literal_numbers)==1 and
            any(d.get('applicability_verified') and d.get('effective_from') and
                '/'.join(normalize(d.get('document_number') or '').split('/')[:2]) in literal_numbers and
                date.fromisoformat(d['effective_from'])>(state.get('as_of') or request.as_of or local_date())
                for d in (state['release'] or {}).get('documents',[])))
        article=re.search(r'\bdieu\s+(\d+[a-z]?)\b',question)
        named=[]
        for doc in (state['release'] or {}).get('documents',[]):
            number=normalize(doc.get('document_number') or '')
            title=re.sub(r'^luat so \S+\s+luat\s+','luat ',normalize(doc['title'])).rstrip('.')
            year=re.search(r'/(\d{4})/',number)
            law_match=bool(year and title.startswith('luat ') and 'sua doi' not in title
                and re.search(r'\b'+re.escape(re.sub(r'\s+\d{4}$','',title))+r'(?:\s+nam)?\s+'+year[1]+r'\b',question))
            if (number and number in question) or law_match:named.append(doc['id'])
        legal_topic=any(term in question for term in ('thu hoi','boi thuong','tai dinh cu','quy hoach','dat dai','khieu nai','quyen su dung dat','ho tro'))
        unrelated=any(term in question for term in ('phac do dieu tri','lieu khang sinh','chan doan benh','ly hon','luat hoa ky','luat hoa ki'))
        freshness=('du lieu' in question and any(t in question for t in ('chatbot','kiem tra nguon'))
                   and any(t in question for t in ('bao dam','cap nhat','qua han')))
        place_question=('huyen' in question and 'cu' in question and 'xa' in question
                        and any(t in question for t in ('doi','moi','dia ban')))
        unsupported_project = request.project in {'songhong','olympic'} or any(
            name in question for name in ('song hong','olympic'))
        if unsupported_project:
            state['unsupported_project'] = True
            state['plan'] = Plan(out_of_scope=True)
            await self.event(state,'routing','Chỉ hỗ trợ Vành đai 4; không có dữ liệu dự án khác trong corpus đang phục vụ.')
        elif freshness:
            state['freshness_question']=True
            state['plan']=Plan()
            await self.event(state,'routing','Câu hỏi về mức cập nhật dữ liệu; đối chiếu metadata, không suy hiệu lực văn bản.')
        elif unrelated and not legal_topic:
            state['plan']=Plan(out_of_scope=True)
            await self.event(state,'routing','Câu hỏi thuộc lĩnh vực ngoài phạm vi pháp luật đất đai và quy hoạch Hà Nội.')
        elif literal_numbers-known_numbers:
            state['unsupported_references']=sorted(literal_numbers-known_numbers)
            state['plan']=Plan()
            await self.event(state,'routing','Không có văn bản được viện dẫn đã kiểm chứng trong corpus; không xác nhận nội dung hoặc yêu cầu người dùng bổ sung luật giả định.')
        elif private_entitlement_check(request.message):
            tool='search_project' if request.project else 'search_law'
            state['plan']=Plan(tools=[ToolCall(name=tool,query=request.message[:1000])])
            await self.event(state,'routing','Yêu cầu xác nhận quyền lợi hộ cụ thể cần hồ sơ; tra cứu nguồn và hỏi dữ kiện trước khi kết luận.',tool)
        elif place_question:
            state['plan']=Plan(tools=[ToolCall(name='normalize_place',query=request.message[:1000])])
            await self.event(state,'routing','Đối chiếu tên địa bàn cũ/mới trước khi xác định phạm vi hồ sơ.','normalize_place')
        elif contextual_query!=request.message:
            state['plan']=Plan(tools=[ToolCall(name='search_law',query=contextual_query[:1000])])
            await self.event(state,'routing','Đã đối chiếu tham chiếu với nguồn trong lượt trả lời trước; tiếp tục tra văn bản đó.','search_law')
        elif direct_effectivity or future_date_question:
            state['plan']=Plan(tools=[ToolCall(name='search_law',query=request.message[:1000])])
            await self.event(state,'routing','Đã nhận diện số văn bản và yêu cầu kiểm tra hiệu lực; dùng tra cứu trực tiếp.',
                             'search_law')
        elif article and len(named)==1:
            state['plan']=Plan(tools=[ToolCall(name='open_article',document_id=named[0],
                locator=f'Điều {article[1]}',query=request.message[:1000])])
            await self.event(state,'routing','Đã nhận diện văn bản và điều được người dùng chỉ rõ; mở nguồn tương ứng.',
                             'open_article',named)
        elif legal_topic and not article:
            # Without an explicit provision, search the citizen's actual question.
            # A speculative article choice can discard the governing principle
            # and spend a model request before evidence has even been retrieved.
            tool='search_project' if request.project else 'search_law'
            state['plan']=Plan(tools=[ToolCall(name=tool,query=request.message[:1000])])
            await self.event(state,'routing','Chưa có điều khoản chỉ định; tìm chứng cứ từ câu hỏi gốc trước khi tổng hợp.',tool)
        else:
            catalogue=self.catalogue(state['release'])
            suggested=await asyncio.to_thread(self.store.article_candidates,request.message,
                                              state['release']['id'],state['as_of'],request.project)
            # Keep the planner below the free provider's per-minute budget.
            # These are source-derived candidates, not benchmark answers; a
            # search_law call can still search the whole eligible corpus.
            suggested = suggested[:12]
            candidate_ids = {item['document_id'] for item in suggested}
            catalogue = [item for item in catalogue if item['id'] in candidate_ids] if candidate_ids else catalogue[:12]
            catalogue_fields=None
            if self.provider.settings.llm_provider == 'groq':
                catalogue_fields=['id','document_number','title','project','effective_from','effective_to']
                catalogue=[[d['id'],d['document_number'],d['title'][:120],d['project'],
                            d['effective_from'],d['effective_to']] for d in catalogue]
            try:
                state["plan"] = await self.provider.generate(Plan,
                    "Select at most three read-only tool calls: search_law for legal evidence; search_project for project records; "
                    "open_article for a known document_id and locator; check_effectivity for a known document; "
                    "candidate_articles contain actual source headings, not conclusions. Prefer opening the relevant "
                    "article(s) for a substantive legal question; search_law can supplement unknown provisions. "
                    "For procedural timing or safeguards, seek the governing principle before benefit categories. "
                    "Match the provision object: household compensation differs from administrative implementation expenses. "
                    "For a question asking the categories/types of a rule, open its overview/list provision first, "
                    "not just a specialized provision about one category. Every final claim must be standalone: repeat its actor and material prerequisites rather than referring to other claims. The catalogue is a bounded suggestion "
                    "list, not the full corpus; use search_law if it does not cover the question. "
                    "normalize_place for place aliases. Use IDs from catalogue, never invent IDs. "
                    "Prefer one call for a simple question; use search_law when the document or provision is unknown. "
                    "Out_of_scope only for questions unrelated to Hanoi land law/planning. General rules need no invented private case. "
                    "Missing facts are private-case land type, papers and decision/plan dates, in Vietnamese. "
                    "Do not ask the user to supply laws or rules: retrieve them. coverage_gaps are unavailable sources, "
                    "not evidence; search for available related acts instead.",
                    {"question": redact(request.message), "project": request.project, "as_of": str(state["as_of"]),
                     "history": state["history"], "catalogue": catalogue, 'catalogue_fields':catalogue_fields,
                     "candidate_articles":suggested,
                     "coverage_gaps":self.relevant_gaps(state)}, state["budget"])
            except ProviderUnavailable as exc:
                if not exc.format_failure:raise
                prior=next((m['content'] for m in reversed(state['history']) if m['role']=='user'),'')
                query=(prior[:500]+' '+request.message) if prior else request.message
                tool='search_project' if request.project else 'search_law'
                state['plan']=Plan(tools=[ToolCall(name=tool,query=query[:1000])])
                await self.event(state,'routing','Planner chưa trả đúng schema; dùng tra cứu chỉ đọc và vẫn kiểm chứng câu trả lời.',tool)
            # Internal identifiers and dates already available in the source
            # catalogue are tool inputs, not facts a citizen must supply.
            state['plan'].missing_facts=public_missing_facts(state['plan'].missing_facts,state['release'])
        state['private_entitlement_check']=private_entitlement_check(request.message)
        personal=bool(re.search(r'\btoi\b',question)) or any(t in question for t in ('cua minh','nha minh','ho so nay','thua dat nay','bao nhieu tien','may can','chac chan'))
        general=not personal and any(t in question for t in ('dieu kien','khac nhau','nhom','dong nghia','theo dieu','quy dinh','co luon','co nen','nhung buoc','nguyen tac','doi tuong','can kiem tra','phan biet','co phai','tu dong','co duoc'))
        state['general_rule_question']=general
        if general:state['plan'].missing_facts=[]
        if state['private_entitlement_check']:
            state['plan'].missing_facts=list(dict.fromkeys(state['plan'].missing_facts+[
                'Loại đất, tình trạng giấy tờ quyền sử dụng đất và nhà ở, chỉ cung cấp thông tin đã ẩn danh.',
                'Ngày, căn cứ trong thông báo/quyết định thu hồi đất và phương án bồi thường, hỗ trợ, tái định cư.',
                'Có phải di chuyển chỗ ở, còn nhà hoặc đất ở khác tại địa bàn hay không; hồ sơ xác định điều kiện bồi thường đất ở.',
                'Vị trí xã/thôn và ranh thu hồi trong hồ sơ; thông tin tổng quan dự án chưa xác định quyền lợi của từng hộ.'
            ]))[:6]
        await self.event(state, "plan", f"Đã chọn {len(state['plan'].tools)} công cụ; chế độ {request.mode}.")
        return state

    @staticmethod
    def catalogue(release):
        return [{"id": d["id"], "title": d["title"], 'document_number':d.get('document_number'), "project": d.get("project"),
                 'issued_on':d.get('issued_on'),'effective_from':d.get('effective_from'),'effective_to':d.get('effective_to')}
                for d in (release or {}).get("documents", [])][:100]

    async def search(self, state, query, project=None):
        vector = None
        try:
            vector = await self.provider.embed(query, query=True,budget=state['budget'],release=state['release'])
        except (ProviderUnavailable, RateLimited):
            state['retrieval_degraded']=True
            await self.event(state, "retrieval", "Embedding chưa khả dụng; dùng tìm kiếm từ khóa trong lượt này.")
        hits = await asyncio.to_thread(self.store.search, query, vector, project,
                                      (state["release"] or {}).get("id"), (state['release'] or {}).get('embedding_model', self.provider.settings.embedding_model),state['as_of'])
        # An explicitly requested missing historical document can still have a
        # verified replacement. Open that operative clause before generic hits.
        release = state['release'] or {}
        requested = {g['document_id'] for g in release.get('coverage_gaps', [])
                   if normalize(g.get('document_number', '')).split('/qd')[0] in normalize(query)
                   and g.get('document_number')}
        requested.update(d['id'] for d in release.get('documents',[]) if d.get('document_number')
            and normalize(d['document_number']).split('/qd')[0] in normalize(query))
        priority = {}
        catalogue={d['id']:d for d in release.get('documents',[])}
        for relation in release.get('relations', []) + release.get('unresolved_relations', []):
            if relation['target_id'] in requested and relation['type'] == 'replaces' and state['budget'].tool_calls < 12:
                source=catalogue.get(relation['source_id'],{})
                starts=source.get('effective_from')
                if starts and date.fromisoformat(starts)>state['as_of'] and relation['source_id'] not in requested:
                    continue
                state['budget'].tool()
                doc = await asyncio.to_thread(self.store.open_document, relation['source_id'], release['id'],
                                             relation.get('source_locator') or relation.get('locator'))
                if doc:
                    for chunk in doc.chunks:
                        priority[chunk.id] = Evidence(chunk=chunk, document=doc)
        # Keep future sources as candidates, but do not let an unrequested
        # future replacement displace the acts relevant at the question date.
        hits.sort(key=lambda hit:(hit.document.id in requested,
            applicability(hit.document,state['as_of'],hit.chunk)!='future'),reverse=True)
        for hit in hits:
            priority.setdefault(hit.chunk.id, hit)
        return list(priority.values())[:8]

    async def tools(self, state):
        if state["plan"].out_of_scope or state.get('freshness_question') or state.get('unsupported_references') or not state["release"]:
            return state
        if state.get('private_entitlement_check'):
            await self.event(state, 'tool', 'Thiếu hồ sơ cá nhân; hỏi bổ sung trước khi truy xuất quy định áp dụng.')
            return state
        if state["rounds"]:
            calls = [ToolCall(name="search_law", query=state["verification"].followup_query or state["request"].message)]
        else:
            calls = state["plan"].tools or [ToolCall(name="search_law", query=state["request"].message)]
        release_id = state["release"]["id"]
        previous_evidence=state['evidence']
        # Fresh evidence must enter the bounded context on the second round.
        found = {} if state['rounds'] else {e.chunk.id:e for e in previous_evidence}
        for call in calls:
            if state['budget'].tool_calls>=12:
                break
            state["budget"].tool()
            results = []
            if call.name in {"search_law", "search_project"}:
                results = await self.search(state, call.query or state["request"].message, state["request"].project)
            elif call.name in {"open_article", "check_effectivity"}:
                doc = None if not call.document_id else (await asyncio.to_thread(self.store.open_effectivity,call.document_id,release_id)
                       if call.name=='check_effectivity' else
                       await asyncio.to_thread(self.store.open_document, call.document_id, release_id, call.locator, call.query or state['request'].message))
                if doc:
                    results = [Evidence(chunk=c, document=doc) for c in doc.chunks
                               if call.name=='check_effectivity' or not call.locator or re.search(r'Điều\s+\d+',call.locator,re.IGNORECASE)
                               or normalize(call.locator) in normalize(c.locator)][:3]
                if not results and state['budget'].tool_calls<12:
                    state['budget'].tool()
                    results=await self.search(state,state['request'].message,state['request'].project)
                    await self.event(state,'tool','Không mở được tài liệu/điều khoản yêu cầu; đã tìm căn cứ và văn bản tác động trong corpus.','search_law',
                                     sorted({e.document.id for e in results}))
            elif call.name == "normalize_place":
                aliases = state["release"].get("place_aliases", [])
                matched = resolve_places(aliases, call.query or state["request"].message, state["as_of"])
                if not matched or any(m['normalization_status']!='verified' for m in matched):
                    state['place_clarification']=True
                    state['plan'].missing_facts=['Tên xã/phường, thôn hoặc tổ dân phố trong hồ sơ cũ; địa chỉ chỉ ở mức đã ẩn danh.',
                        'Thời điểm lập hồ sơ và nguồn xác nhận địa bàn sau sắp xếp.',
                        'Ranh giới dự án và thông báo/quyết định thu hồi đối với thửa đất, nếu cần đối chiếu phạm vi.']
                state["tool_notes"].append({"tool": call.name, "matches": matched[:6]})
                await self.event(state, "tool", f"Tìm thấy {len(matched)} ánh xạ địa bàn có nguồn; thiếu ánh xạ thì cần hỏi lại.", call.name)
            for item in results:
                item.applicability = applicability(item.document, state["as_of"],item.chunk)
                found[item.chunk.id] = item
            await self.event(state, "tool", f"Thu được {len(results)} đoạn chứng cứ.", call.name,
                             sorted({e.document.id for e in results}))
        # Follow legal relationships; deterministic scope checks are never delegated entirely to the LLM.
        catalogue = {d['id']: d for d in state['release']['documents']}
        opened = state.setdefault('opened_relations', set())
        opened.update((e.document.id, e.chunk.locator) for e in found.values())
        operative_ids=set()
        question=normalize(state['request'].message)
        requested_numbers=set(re.findall(r'(?<![\d/])\d{1,6}/(?:19|20)\d{2}(?!/\d)',question))
        requested_docs={d['id'] for d in catalogue.values() if any(
            number in normalize(d.get('document_number') or '') for number in requested_numbers)}
        wanted_types={kind for phrase,kind in [('bai bo','repeals'),('thay the','replaces'),('sua doi','amends')]
                      if phrase in question}
        temporal_question=bool(wanted_types) or any(term in question for term in ('hieu luc','chuyen tiep')) or bool(
            re.search(r'\b(?:truoc|cu)\b',question))
        def starts_by_question(doc_id):
            starts=catalogue.get(doc_id,{}).get('effective_from')
            return bool(starts and date.fromisoformat(starts)<=state['as_of'])
        doc_ids=list(dict.fromkeys(e.document.id for e in found.values()))
        doc_ids.sort(key=lambda doc_id:(doc_id in requested_docs,starts_by_question(doc_id)),reverse=True)
        for doc_id in doc_ids[:4]:
            if state["budget"].tool_calls >= 12:
                break
            state["budget"].tool()
            relations = await asyncio.to_thread(self.store.relations, doc_id, release_id)
            relations = [relation for relation in relations
                         if relation_may_affect(relation, doc_id, list(found.values()))]
            relations.sort(key=lambda relation: (
                starts_by_question(relation.source_id),
                relation.type in wanted_types,
                relation.source_id in requested_docs,
                relation.target_id == doc_id,
                catalogue.get(relation.source_id, {}).get('effective_from') or ''), reverse=True)
            for relation in relations:
                if state['budget'].tool_calls >= 12:
                    break
                source_start=catalogue.get(relation.source_id,{}).get('effective_from')
                if (source_start and date.fromisoformat(source_start)>state['as_of']
                        and relation.source_id not in requested_docs):
                    # Keep the relationship in metadata, but do not crowd a
                    # historical answer with an unrequested future amendment.
                    continue
                if (relation.source_id==doc_id and relation.type in {'replaces','repeals','transition'}
                        and not temporal_question and relation.target_id not in requested_docs):
                    # Validity remains in relation metadata. An ordinary lookup
                    # of a current rule does not need the repealed act's preamble
                    # or unrelated old-file transitions in its answer context.
                    continue
                if relation.source_id==doc_id and relation.source_locator and state['budget'].tool_calls<12:
                    numbers=re.findall(r'Điều\s+(\d+)',relation.source_locator)
                    if not any(e.document.id==doc_id and any(e.chunk.locator==f'Điều {n}' for n in numbers) for e in found.values()):
                        state['budget'].tool()
                        source=await asyncio.to_thread(self.store.open_document,doc_id,release_id,relation.source_locator,state['request'].message)
                        if source:
                            for chunk in source.chunks:
                                operative_ids.add(chunk.id)
                                found.setdefault(chunk.id,Evidence(chunk=chunk,document=source,
                                    applicability=applicability(source,state['as_of'],chunk)))
                            await self.event(state,'tool','Đã mở điều khoản nguồn của quan hệ sửa đổi/thay thế.','open_article',[doc_id])
                related_id = relation.source_id if relation.target_id == doc_id else relation.target_id
                locator = (relation.source_locator or relation.locator) if related_id == relation.source_id else " ".join(relation.target_locators)
                if (related_id, locator) in opened:
                    continue
                if state['budget'].tool_calls >= 12:
                    break
                state['budget'].tool()
                opened.add((related_id, locator))
                affected_locators=' '.join(dict.fromkeys(e.chunk.locator for e in found.values() if e.document.id==doc_id))[:250]
                relation_query=(state['request'].message[:700]+' '+affected_locators)[:1000]
                doc = await asyncio.to_thread(self.store.open_document, related_id, release_id, locator,relation_query)
                if doc:
                    for chunk in relation_chunks(doc, locator):
                        if related_id==relation.source_id:operative_ids.add(chunk.id)
                        found.setdefault(chunk.id, Evidence(chunk=chunk, document=doc,
                                                           applicability=applicability(doc, state["as_of"],chunk)))
                    await self.event(state, 'tool', 'Đã mở văn bản có quan hệ pháp lý để đối chiếu phạm vi.',
                                     'open_article', [related_id])
            await self.event(state, "applicability", f"Đã kiểm tra {len(relations)} quan hệ pháp lý theo thời điểm.", "check_effectivity", [doc_id])
        for item in previous_evidence:
            found.setdefault(item.chunk.id,item)
        # Keep existing hits stable and add parent text, capped to a bounded context.
        parent_ids=set()
        for item in list(found.values())[:8]:
            if item.chunk.parent_id:
                parent = await asyncio.to_thread(self.store.chunk, item.chunk.parent_id, release_id)
                if parent:
                    parent_ids.add(parent.id)
                    found.setdefault(parent.id, Evidence(chunk=parent, document=item.document, applicability=item.applicability))
        candidates=list(found.values())
        # Relationship expansion can fill every secondary slot before parents
        # are appended. Keep the complete context of primary hits before extra
        # relation passages; unrepresented amendments still veto claims later.
        secondary=sorted(candidates[8:],key=lambda item:(item.chunk.id in parent_ids,
                                                       item.chunk.id in operative_ids),reverse=True)
        state["evidence"] = candidates[:8]+secondary[:8]
        state["rounds"] += 1
        return state

    def context(self, state):
        return [{"citation_id": e.chunk.id, "document_id": e.document.id, "title": e.document.title,
                 'document_number':e.document.document_number,'page':e.chunk.page,
                 "kind": e.document.source_kind, "locator": e.chunk.locator, "text": e.chunk.text,
                 "applicability": e.applicability, "effective_from": str(e.document.effective_from),
                 "effective_to": str(e.document.effective_to),
                 "provision_validity": e.document.provision_validity,
                 'source_review_notes':e.document.source_review_notes,
                 "legal_relations": self.relation_context(e, state)} for e in state["evidence"]]

    @staticmethod
    def relevant_gaps(state):
        question=normalize(state['request'].message)
        selected={e.document.id for e in state.get('evidence',[])}
        missing={r['source_id'] for r in (state.get('release') or {}).get('unresolved_relations',[])
                 if r['target_id'] in selected and r['type'] in {'amends','repeals','overrides'}}
        return [g for g in (state.get('release') or {}).get('coverage_gaps',[]) if g['document_id'] in missing
                or (g.get('document_number') and normalize(g['document_number']).split('/qd')[0] in question)]

    @staticmethod
    def relevant_unresolved(state):
        selected={e.document.id for e in state.get('evidence',[])}
        selected.update(g['document_id'] for g in Agent.relevant_gaps(state))
        return [r for r in (state.get('release') or {}).get('unresolved_relations',[])
                if {r['source_id'],r['target_id']} & selected]

    def prompt_context(self,state,selected_ids=None):
        """Send each document's legal relationships once, preserving every passage.

        Repeating a long amendment graph for each chunk can overflow a free
        model's context and distract from the actual operative text.
        """
        passages,documents=[],{}
        candidates=self.context(state)
        if self.provider.settings.llm_provider == 'groq' and selected_ids is None:
            # A parent is an existing, verbatim source passage, not a summary.
            # Prefer it to contained children only when it can enter the bounded
            # prompt. Never change citation IDs/text during verification.
            parents={e.chunk.id:e for e in state['evidence'] if e.chunk.id.endswith('-parent')}
            by_id={item['citation_id']:item for item in candidates}
            covered={}
            for evidence in state['evidence']:
                parent=parents.get(evidence.chunk.parent_id)
                if (parent and parent.document.id==evidence.document.id
                        and parent.chunk.locator.split(' · ')[0]==evidence.chunk.locator.split(' · ')[0]
                        and evidence.chunk.text in parent.chunk.text
                        and len(parent.chunk.text)<=4000):
                    covered[evidence.chunk.id]=parent.chunk.id
            unique={}
            for item in candidates:
                key=covered.get(item['citation_id'],item['citation_id'])
                unique.setdefault(key,by_id[key])
            candidates=list(unique.values())
            group_order={}
            for item in candidates:
                group_order.setdefault((item['document_id'],item['locator'].split(' · ')[0]),len(group_order))
            question=normalize(state['request'].message) if state.get('request') else ''
            numbers=set(re.findall(r'(?<![\d/])\d{1,6}/(?:19|20)\d{2}(?!/\d)',question))
            articles=set(re.findall(r'\bdieu\s+(\d+[a-z]?)\b',question))
            references=re.findall(r'\b(?:diem\s+[a-zđ]\s+)?khoan\s+\d+\s+dieu\s+\d+[a-z]?\b',question)
            terms=set(re.findall(r'[a-z0-9]{3,}',question))-{'quyet','dinh','dieu','ngay','theo','khong','van','ban','toi'}
            temporal=any(term in question for term in ('hieu luc','thay the','bai bo','ap dung ngay'))
            def relevant(item):
                body=normalize(item['text']);locator=normalize(item['locator'])
                exact_article=any(re.match(rf'^dieu {n}(?:\s|$)',locator) for n in articles)
                body_numbers=sum(n in body for n in numbers)
                reference_matches=sum(reference in body for reference in references)
                document_match=any(n in normalize(item.get('document_number') or '') for n in numbers)
                operative=temporal and any(term in body for term in ('co hieu luc','thay the','bai bo'))
                overlap=len(terms & set(body.split()))/max(1,len(body.split()))**.5
                heading=re.match(r'dieu\s+\d+[a-z]?\s*[.:]\s*(.*?)(?:\s+1\.\s|$)',body)
                heading_overlap=len(terms & set(heading[1].split()))/max(1,len(set(heading[1].split()))) if heading else 0
                timely=not temporal or item['applicability']!='future' or document_match
                # RRF already ranks substantive evidence. Keep continuations
                # with that article instead of letting keyword-dense benefits
                # displace the governing principle in the bounded prompt.
                group=group_order[(item['document_id'],item['locator'].split(' · ')[0])]
                return (exact_article and (document_match or not numbers),timely,reference_matches,body_numbers,operative,document_match,item['applicability']=='current',-group,heading_overlap,overlap)
            candidates=sorted(candidates,key=relevant,reverse=True)
            named_docs={item['document_id'] for item in candidates if any(
                n in normalize(item.get('document_number') or '') for n in numbers)}
            exact_references=[item for item in candidates if item['document_id'] in named_docs
                and any(reference in normalize(item['text']) for reference in references)]
            if exact_references:
                # An explicit point/clause reference already has a complete
                # source paragraph. Nearby provisions about different actors
                # are not substitutes. Retain connected legal evidence, too,
                # so an effective amendment/transition cannot disappear.
                related=set()
                for relation in (state['release'] or {}).get('relations',[]):
                    if {relation['source_id'],relation['target_id']} & named_docs:
                        related.update({relation['source_id'],relation['target_id']}-named_docs)
                exact_ids={item['citation_id'] for item in exact_references}
                candidates=[item for item in candidates if item['citation_id'] in exact_ids
                            or item['document_id'] in related]
        for item in candidates:
            if selected_ids is not None and item['citation_id'] not in selected_ids:
                continue
            document_id=item['document_id']
            metadata={key:item[key] for key in (
                'document_id','title','document_number','kind','effective_from','effective_to',
                'provision_validity','legal_relations','source_review_notes')}
            if self.provider.settings.llm_provider == 'groq':
                fields=['source_id','target_id','type','source_locator','target_locators',
                        'target_locators_complete','source_effective_from','source_verified']
                metadata['legal_relation_fields']=fields
                metadata['legal_relations']=[[relation.get(key) for key in fields]
                                             for relation in item['legal_relations']]
            documents.setdefault(document_id,metadata)
            passage={key:item[key] for key in (
                'citation_id','document_id','page','locator','text','applicability')}
            if self.provider.settings.llm_provider == 'groq' and selected_ids is None:
                # Select whole passages rather than truncating clauses. Retrieval
                # still retains eight primary hits and related evidence in trace.
                projected_docs={k:v for k,v in documents.items()
                                if k in {p['document_id'] for p in passages} | {document_id}}
                context_limit=7000
                if len(json.dumps([passages+[passage],list(projected_docs.values())],ensure_ascii=False))>context_limit:
                    if not any(p['document_id']==document_id for p in passages):documents.pop(document_id,None)
                    continue
            passages.append(passage)
        return passages,list(documents.values())

    def relation_context(self, evidence, state):
        docs = {d["id"]: d for d in (state["release"] or {}).get("documents", [])}
        result = []
        for relation in (state["release"] or {}).get("relations", []):
            if evidence.document.id not in {relation["source_id"], relation["target_id"]}:
                continue
            if relation.get('target_locators_complete') and not relation_may_affect(
                    Relation.model_validate(relation),evidence.document.id,state['evidence']):
                continue
            source = docs.get(relation["source_id"])
            model_relation={key:value for key,value in relation.items() if key!='source_url'}
            result.append({**model_relation, "source_effective_from": (source or {}).get("effective_from"),
                           "source_verified": (source or {}).get("applicability_verified", False),
                           "scope_note": "Phạm vi từng điều khoản; không suy ra toàn văn bị bãi bỏ từ quan hệ sửa đổi/bãi bỏ một phần."})
        return result

    async def synthesize(self, state):
        state['source_fact_id']=None
        state['source_fact_type']=None
        if state["plan"].out_of_scope:
            state["draft"] = Draft(status="insufficient_evidence", summary="Câu hỏi nằm ngoài phạm vi đất đai và quy hoạch Hà Nội.",out_of_scope=True)
        elif state.get('freshness_question') or state.get('unsupported_references'):
            state['draft']=Draft(status='insufficient_evidence')
        elif state.get('place_clarification'):
            state['draft']=Draft(status='clarification_needed',missing_facts=state['plan'].missing_facts)
        elif state.get('private_entitlement_check'):
            # The corpus contains public law/project records, never this
            # household's administrative file. Do not turn a general rule
            # into a guarantee, even if the model's verifier would approve it.
            state['draft']=Draft(status='clarification_needed',
                missing_facts=state['plan'].missing_facts,
                next_steps=['Đối chiếu hồ sơ đã ẩn danh với văn bản áp dụng và điều khoản chuyển tiếp; chưa thể khẳng định suất tái định cư hoặc tiền bồi thường cho hộ cụ thể.'])
        elif not state["evidence"]:
            state["draft"] = Draft(status="insufficient_evidence", summary="Chưa tìm được chứng cứ trong bộ dữ liệu đã công bố.",
                                   missing_facts=state["plan"].missing_facts)
        elif (future:=self.future_commencement(state)) is not None:
            # The source proves commencement, not every historical case's
            # transition. State only that verified date and ask for case facts.
            date_text=future.document.effective_from.strftime('%d/%m/%Y')
            state['source_fact_id']=future.chunk.id
            state['source_fact_type']='future_commencement'
            state['draft']=Draft(status='clarification_needed',summary='',
                claims=[Claim(kind='applicability',
                    text=f'{future.document.document_number} có hiệu lực thi hành từ ngày {date_text}. '
                         f'Văn bản này chưa có hiệu lực tại ngày {state["as_of"].strftime("%d/%m/%Y")}.',
                    citation_ids=[future.chunk.id])],
                missing_facts=['Ngày ra quyết định thu hồi đất và ngày phê duyệt phương án bồi thường.',
                               'Loại đất và tình trạng giấy tờ của hồ sơ, chỉ cung cấp thông tin đã ẩn danh.'],
                next_steps=['Đối chiếu căn cứ và điều khoản chuyển tiếp trong quyết định, phương án xử lý hồ sơ.'])
        elif (news:=self.planning_task_news(state)) is not None:
            state['source_fact_id']=news.chunk.id
            state['source_fact_type']='planning_task_news'
            state['draft']=Draft(status='answered',claims=[self.planning_task_claim(news)])
        elif (partial:=self.partial_repeal(state)) is not None:
            item,relation,target=partial
            state['source_fact_id']=item.chunk.id
            state['source_fact_type']='partial_repeal'
            state['draft']=Draft(status='answered',claims=[self.partial_repeal_claim(item,relation,target)])
        elif (replacement:=self.replacement_fact(state)) is not None:
            item,target=replacement
            state['source_fact_id']=item.chunk.id
            state['source_fact_type']='replacement'
            state['draft']=Draft(status='answered',claims=[self.replacement_claim(item,target,state['as_of'])])
        else:
            contexts,documents=self.prompt_context(state)
            aliases={item['citation_id']:f'C{index+1}' for index,item in enumerate(contexts)}
            contexts=[{**item,'citation_id':aliases[item['citation_id']]} for item in contexts]
            state["draft"] = await self.provider.generate(Draft,
                "Answer the actual question in Vietnamese. Use ONE concise, independently qualified claim by default; "
                "at most three for genuinely separate requested propositions. Put ALL legal content in claims; summary "
                "is not displayed. citation_ids must be allowed C1/C2 aliases, never document IDs. "
                "Prefer the source's exact operative wording. Each claim must itself retain its actor, land/asset scope, "
                "eligibility prerequisites, OR alternatives, exceptions, consequence and applicable time. Do not rely "
                "on a different claim for a missing condition. Cite every passage needed, including continuations. "
                "Use the complete parent passage when a child omits conditions; a title/preamble proves no rule. "
                "Only answer what was asked. Do not add unasked rates, durations, amounts, exhaustive actor lists or "
                "neighboring benefits. Quantities needed to state an eligibility condition must retain their scope. "
                "Do not turn a condition in the user's question into a new legal trigger in the source. "
                "For document alternatives, retain the prerequisite 'trường hợp thuộc khoản ...' in the SAME claim; "
                "explain the alternatives with OR, never AND. An actor category is not a qualifying document. "
                "For assistance catalogues, distinguish the categories from eligibility: not every household "
                "automatically receives every category. Preserve income, approval-date and exclusion conditions "
                "when the operative source uses them to define an eligible actor. Do not invent conditions from "
                "cross-references: explain them only with actual text, otherwise disclose the missing scope. "
                "Preserve exact article/clause/point references, including the scope of partial amendments. Use "
                "bullets for summary lists, not invented legal point letters or numbered clauses. Distinguish "
                "Chủ tịch UBND from UBND and household compensation from implementation/coercion expenses. "
                "current evidence supports current rules; historical requires a disclosed historical question or "
                "operative transition; future supports only applicability saying NOT yet effective with the "
                "source-proven commencement. provision_specific requires the actual clause dates. Issue dates "
                "are not commencement. Replacement alone does not decide old files: include a next_step to check "
                "recovery/approved-plan dates and transitions before applying a replacement to an old file. "
                "No whole-act repeal inferred from a partial change. Respect source review notes, special policies "
                "and unresolved dependencies. coverage_gaps and history are not legal evidence. "
                "General rules need no invented private file. For personal rights ask for land type, papers and "
                "recovery/approved-plan dates, never ask the citizen to provide law already available. Never "
                "guarantee parcel/household rights or money from general project facts. official_news is context "
                "only; planning-task approval does not establish approved plans or household recovery. "
                "If the main proposition lacks proof, use insufficient_evidence rather than substituting a nearby "
                "rule. next_steps are generic checks, never unchecked legal conditions. Repair previous_issues "
                "from supplied evidence without broadening the answer. Out-of-scope topics get no legal/medical advice.",
                {"question": redact(state["request"].message), "as_of": str(state["as_of"]), "history": state["history"],
                 "missing_facts": state["plan"].missing_facts, "tool_results": state["tool_notes"], "evidence": contexts,
                 "documents":documents,
                 'allowed_citation_ids':list(aliases.values()),
                 "coverage_gaps": self.relevant_gaps(state),
                 'question_kind':'general_rule' if state.get('general_rule_question') else 'case_or_other',
                 "unresolved_relations": self.relevant_unresolved(state),
                 'context_selection':{'complete_passages':len(contexts),'retrieved_candidates':len(state['evidence']),
                                      'omitted_candidates_are_not_citable':True},
                 "previous_issues": state.get("verification", Verification()).issues}, state["budget"])
            actual={value:key for key,value in aliases.items()}
            state['draft'].claims=[claim.model_copy(update={'citation_ids':[actual.get(key,key) for key in claim.citation_ids]})
                                   for claim in state['draft'].claims]
        await self.event(state, "synthesis", "Đã tạo bản trả lời; đang kiểm tra trước khi hiển thị.")
        return state

    @staticmethod
    def planning_task_news(state):
        question=normalize(state['request'].message)
        if ('nhiem vu quy hoach' not in question or 'do an' not in question
                or not any(t in question for t in ('dong nghia','du ket luan'))):return None
        references=re.findall(r'\b\d{1,6}/qd-ubnd\b',question)
        for item in state['evidence']:
            body=normalize(item.chunk.text)
            position=body.find('phe duyet nhiem vu quy hoach')
            prefix=body[max(0,position-160):position]
            proposed=bool(re.search(r'\b(?:khong|chua|se|du kien|de xuat|xin|du thao|kien nghi)\b',prefix))
            if (item.document.source_kind=='official_news' and position>=0 and not proposed
                    and all(ref in body for ref in references)):
                return item
        return None

    @staticmethod
    def planning_task_claim(item):
        return Claim(kind='context',text='Nguồn được trích dẫn công bố việc phê duyệt nhiệm vụ quy hoạch. '
            'Đây là thông tin bối cảnh, chưa đủ để chứng minh toàn bộ đồ án và việc thu hồi đất từng hộ đã được phê duyệt; '
            'cần đối chiếu quyết định phê duyệt đồ án và hồ sơ thu hồi tương ứng.',citation_ids=[item.chunk.id])

    @staticmethod
    def future_commencement(state):
        question=normalize(state['request'].message)
        if 'ap dung ngay' not in question:return None
        numbers=set(re.findall(r'(?<![\d/])\d{1,6}/(?:19|20)\d{2}(?!/\d)',question))
        for item in state['evidence']:
            doc=item.document
            number='/'.join(normalize(doc.document_number or '').split('/')[:2])
            if (number in numbers and doc.applicability_verified and item.applicability=='future'
                    and doc.effective_from in source_effective_dates(item.chunk.text)):
                return item
        return None

    @staticmethod
    def partial_repeal(state):
        question=normalize(state['request'].message)
        if 'bai bo' not in question or not any(term in question for term in ('toan bo','mot phan')):return None
        pattern=r'(?<![\d/])(\d{1,6})/((?:19|20)\d{2})(?!/\d)'
        def number(text):return {f'{int(a)}/{b}' for a,b in re.findall(pattern,normalize(text))}
        requested=number(question)
        if len(requested)!=2:return None
        docs={d['id']:d for d in (state['release'] or {}).get('documents',[])}
        for relation in (state['release'] or {}).get('relations',[]):
            target=docs.get(relation['target_id'])
            if (not target or not target.get('applicability_verified') or relation['type']!='repeals' or not relation.get('target_locators_complete')
                    or not relation.get('target_locators') or not relation.get('source_locator')):continue
            for item in state['evidence']:
                if (item.document.id!=relation['source_id'] or item.applicability!='current'
                        or not item.document.applicability_verified
                        or (number(item.document.document_number or '') | number(target.get('document_number') or '')) != requested
                        or item.chunk.locator!=relation['source_locator']):continue
                source=normalize(item.chunk.text)
                if ('bai bo' in source and number(target.get('document_number') or '') <= number(source)
                        and all(normalize(locator) in source for locator in relation['target_locators'])):
                    return item,relation,target
        return None

    @staticmethod
    def partial_repeal_claim(item,relation,target):
        scope='; '.join(relation['target_locators'])
        return Claim(kind='applicability',text=f'{item.document.document_number} bãi bỏ {scope} của {target["document_number"]}. '
            f'Phạm vi bãi bỏ này là một phần; không phải toàn bộ {target["document_number"]}.',citation_ids=[item.chunk.id])

    @staticmethod
    def replacement_fact(state):
        """Prove an act's replacement, without drawing private-case conclusions."""
        question=normalize(state['request'].message)
        if not any(term in question for term in ('hieu luc','thay the','mau thuan')):return None
        if any(term in question for term in ('ho so','quyen loi','boi thuong','ho tro','tai dinh cu',
                                            'thu tuc','dieu kien','tinh tien','bao nhieu')):return None
        pattern=r'(?<![\d/])(\d{1,6})/((?:19|20)\d{2})(?!/\d)'
        def numbers(text):return {f'{int(a)}/{b}' for a,b in re.findall(pattern,normalize(text))}
        requested=numbers(question)
        if not requested:return None
        docs={d['id']:d for d in (state['release'] or {}).get('documents',[])}
        for relation in (state['release'] or {}).get('relations',[]):
            target=docs.get(relation['target_id'])
            if (relation['type']!='replaces' or relation.get('target_locators') or not target
                    or not target.get('applicability_verified')
                    or not numbers(target.get('document_number') or '')
                    or not numbers(target.get('document_number') or '')<=requested):continue
            for item in state['evidence']:
                source=item.document
                start=source.effective_from
                if (source.id!=relation['source_id'] or not source.applicability_verified
                        or item.applicability!='current' or not start or state['as_of']<start
                        or target.get('effective_to')!=start.isoformat()
                        or start not in source_effective_dates(item.chunk.text)):continue
                body=normalize(item.chunk.text)
                # Require replacement of an act itself, not an article/point,
                # and the target number in that operative replacement clause.
                clause=re.search(r'thay the\s+(?:cac\s+)?(?:quyet dinh|nghi dinh|luat|nghi quyet)\b(.+)',body)
                if (clause and numbers(target.get('document_number') or '')<=numbers(clause[0])
                        and requested<=numbers(clause[0])|numbers(source.document_number or '')):
                    return item,target
        return None

    @staticmethod
    def replacement_claim(item,target,as_of):
        return Claim(kind='applicability',text=f'{target["document_number"]} không còn hiệu lực tại ngày {as_of.strftime("%d/%m/%Y")}; '
            f'{item.document.document_number} thay thế văn bản này từ ngày {item.document.effective_from.strftime("%d/%m/%Y")}.',
            citation_ids=[item.chunk.id])

    async def verify(self, state):
        draft = state["draft"]
        if state.get('freshness_question') or (state.get('place_clarification') and not draft.claims):
            state['verification']=Verification()
            await self.event(state,'verification','Chỉ giải thích giới hạn dữ liệu hoặc hỏi địa bàn còn thiếu; không kết luận quyền lợi hay phạm vi từng thửa.')
            return state
        if state.get('plan',Plan()).out_of_scope or draft.out_of_scope:
            # Finish renders a fixed scope notice and discards all claims.
            state['verification']=Verification()
            await self.event(state,'verification','Chỉ trả thông báo ngoài phạm vi; không có kết luận pháp lý hoặc hướng dẫn chuyên ngành khác.')
            return state
        if not state["evidence"]:
            state["verification"] = Verification()
            return state
        news=self.planning_task_news(state) if state.get('source_fact_type')=='planning_task_news' else None
        if news and news.chunk.id==state.get('source_fact_id') and draft.claims==[self.planning_task_claim(news)]:
            state['verification']=Verification(supported_claim_indexes=[0],supporting_quotes=[
                SupportingQuote(claim_index=0,citation_id=news.chunk.id,quote=news.chunk.text[:1600])])
            await self.event(state,'verification','Đã đối chiếu đoạn công bố nhiệm vụ; chỉ mô tả thông tin bối cảnh và giới hạn chứng cứ, không suy việc thu hồi hộ.')
            return state
        if state.get('private_entitlement_check') and not draft.claims:
            state['verification']=Verification()
            await self.event(state,'verification','Hồ sơ hộ/thửa chưa được cung cấp; chỉ hỏi bổ sung, không suy quyền lợi từ tài liệu công khai.')
            return state
        # This claim is constructed by the server from a source-verified date,
        # not generated prose about an entitlement or a transition. Recheck
        # the literal commencement and chronological comparison as proof.
        future=self.future_commencement(state) if state.get('source_fact_type')=='future_commencement' else None
        if future and future.chunk.id==state['source_fact_id']:
            expected=f'{future.document.document_number} có hiệu lực thi hành từ ngày {future.document.effective_from.strftime("%d/%m/%Y")}. '
            expected+=f'Văn bản này chưa có hiệu lực tại ngày {state["as_of"].strftime("%d/%m/%Y")}.'
            if (draft.status=='clarification_needed' and len(draft.claims)==1
                    and draft.claims[0].kind=='applicability' and draft.claims[0].text==expected
                    and draft.claims[0].citation_ids==[future.chunk.id]
                    and state['as_of']<future.document.effective_from):
                state['verification']=Verification(supported_claim_indexes=[0],supporting_quotes=[
                    SupportingQuote(claim_index=0,citation_id=future.chunk.id,quote=future.chunk.text)])
                await self.event(state,'verification','Đã đối chiếu mốc hiệu lực trực tiếp trong nguồn với ngày hỏi; chưa kết luận quyền lợi hoặc chuyển tiếp hồ sơ.',
                                 'check_effectivity',[future.document.id])
                return state
        partial=self.partial_repeal(state) if state.get('source_fact_type')=='partial_repeal' else None
        if partial:
            item,relation,target=partial
            if (item.chunk.id==state['source_fact_id'] and draft.status=='answered'
                    and draft.claims==[self.partial_repeal_claim(item,relation,target)]):
                state['verification']=Verification(supported_claim_indexes=[0],supporting_quotes=[
                    SupportingQuote(claim_index=0,citation_id=item.chunk.id,quote=item.chunk.text)])
                await self.event(state,'verification','Đã đối chiếu phạm vi bãi bỏ một phần đã rà soát với đúng số văn bản và điều khoản nguồn.',
                                 'check_effectivity',[item.document.id,target['id']])
                return state
        replacement=self.replacement_fact(state) if state.get('source_fact_type')=='replacement' else None
        if replacement:
            item,target=replacement
            if (item.chunk.id==state['source_fact_id'] and draft.status=='answered'
                    and draft.claims==[self.replacement_claim(item,target,state['as_of'])]):
                state['verification']=Verification(supported_claim_indexes=[0],supporting_quotes=[
                    SupportingQuote(claim_index=0,citation_id=item.chunk.id,quote=item.chunk.text)])
                await self.event(state,'verification','Đã đối chiếu số văn bản trong điều khoản thay thế, mốc hiệu lực nguồn và ngày hết hiệu lực đã xác minh của văn bản cũ.',
                                 'check_effectivity',[item.document.id,target['id']])
                return state
        evidence = {e.chunk.id: e for e in state["evidence"]}
        repaired=[]
        for index,claim in enumerate(draft.claims):
            claim_dates=claim_effective_dates(claim.text,state['as_of'])
            if 'hieu luc' not in normalize(claim.text) or not claim_dates:
                continue
            if any(i not in evidence for i in claim.citation_ids):
                continue
            doc_ids={evidence[i].document.id for i in claim.citation_ids}
            if len(doc_ids)!=1:
                continue
            candidates=[e for e in evidence.values() if e.document.id in doc_ids
                        and claim_dates<=source_effective_dates(e.chunk.text)
                        and claim_source_dates(claim.text,state['as_of'])<=dates_in(e.chunk.text)]
            if candidates:
                candidate=min(candidates,key=lambda e:(len(e.chunk.text),e.chunk.id))
                if claim.citation_ids != [candidate.chunk.id]:
                    draft.claims[index]=claim.model_copy(update={'citation_ids':[candidate.chunk.id]})
                    repaired.append(candidate.document.id)
        if repaired:
            await self.event(state,'verification','Đã chọn đúng đoạn quy định ngày hiệu lực trong cùng văn bản trước khi đối chiếu nội dung.',
                             docs=sorted(set(repaired)))
        structural_issues = []
        for index, claim in enumerate(draft.claims):
            if any(i not in evidence for i in claim.citation_ids):
                structural_issues.append(f"Claim {index}: ID trích dẫn không có trong chứng cứ")
            if all(i in evidence and (evidence[i].applicability=='unverified' or
                   (evidence[i].applicability=='future' and claim.kind!='applicability')) for i in claim.citation_ids):
                structural_issues.append(f"Claim {index}: căn cứ chưa xác minh tính áp dụng")
            normalized_claim=normalize(claim.text)
            assistance_list = ('ho tro' in normalized_claim and normalized_claim.count('ho tro') >= 3)
            if assistance_list and re.search(r'\b(?:nha nuoc|moi ho|cac ho).*\bphai (?:thuc hien|duoc|nhan)\b', normalized_claim):
                structural_issues.append(f'Claim {index}: danh mục hỗ trợ không chứng minh nghĩa vụ áp dụng mọi khoản cho mọi trường hợp; cần viết đúng phạm vi ngay trong claim')
            category_count = re.search(r'\b(hai|ba|bon|nam|sau|bay|tam|chin|muoi|\d+)\s+(?:loai|nhom)\s+ho tro(?:\s+chinh)?\b', normalized_claim)
            example_list = category_count and re.search(r'\b(?:vi du|mot so|it nhat|chang han|trong do)\b', normalized_claim[:category_count.start()][-60:])
            if assistance_list and category_count and not example_list:
                cited_passages = [normalize(evidence[c].chunk.text) for c in claim.citation_ids if c in evidence]
                counts = {'hai':2, 'ba':3, 'bon':4, 'nam':5, 'sau':6, 'bay':7, 'tam':8, 'chin':9, 'muoi':10}
                expected = int(category_count[1]) if category_count[1].isdigit() else counts[category_count[1]]
                if not any('bao gom' in text and len(re.findall(r'\b[a-zđ]\)\s+ho tro\b', text)) == expected
                           for text in cited_passages):
                    structural_issues.append(f'Claim {index}: không suy số nhóm hỗ trợ chung từ nhiều điều quy định từng khoản riêng; cần nguồn danh mục và không tự giới hạn số nhóm')
            if ('phai co hop dong giao khoan' in normalized_claim
                    and not any(term in normalized_claim for term in ('nhan giao khoan', 'dat nong nghiep', 'nong truong', 'lam truong'))):
                structural_issues.append(f'Claim {index}: không biến điều kiện hợp đồng giao khoán của nhóm sử dụng đất cụ thể thành điều kiện chung nhận hỗ trợ')
            groups=('cong dong dan cu','to chuc ton giao','to chuc nuoc ngoai','to chuc kinh te','nguoi goc viet nam')
            source_body=normalize(' '.join(evidence[c].chunk.text for c in claim.citation_ids if c in evidence))
            if ('duoc ho tro' in normalized_claim and 'truc tiep san xuat nong nghiep' in normalized_claim
                    and 'tai thoi diem phe duyet phuong an' in source_body
                    and 'thu nhap tu san xuat nong nghiep' in source_body):
                if not ('thu nhap' in normalized_claim and 'thoi diem phe duyet phuong an' in normalized_claim):
                    structural_issues.append(f'Claim {index}: chủ thể trực tiếp sản xuất nông nghiệp thiếu điều kiện thu nhập và thời điểm phê duyệt phương án trong nguồn')
            prefix=re.match(r'^(?:khi|neu|truong hop)\b([^,;.]{0,200})',normalized_claim)
            if prefix and re.search(r'\bchua\b',prefix[1]) and not re.search(r'\bchua\b',source_body):
                structural_issues.append(f'Claim {index}: điều kiện chưa xảy ra trong câu hỏi không được đoạn nguồn xác lập làm căn cứ áp dụng')
            expense=re.search(r'(?:,|\bthi)\s*(?:cac\s+)?chi phi (?:boi thuong|ho tro|tai dinh cu)',normalized_claim)
            if expense and any(t in source_body for t in ('chi phi bao dam','kinh phi to chuc')) and not any(t in normalized_claim[expense.start():] for t in ('to chuc','cuong che','thanh, quyet toan')):
                structural_issues.append(f'Claim {index}: không mở rộng kinh phí tổ chức/cưỡng chế thành các khoản bồi thường, hỗ trợ của hộ')
            if re.search(r'\b\d+\s+lan\s+gia dat',normalized_claim):
                for qualification in ('bang gia dat','han muc'):
                    if qualification in source_body and qualification not in normalized_claim:
                        structural_issues.append(f'Claim {index}: mức hỗ trợ theo lần giá đất thiếu cơ sở bảng giá hoặc hạn mức trong nguồn')
            if ('nhan giao khoan' in normalized_claim and 'tru truong hop' in source_body
                    and any(t in source_body for t in ('nghi huu','nghi mat suc','thoi viec duoc huong tro cap'))
                    and not any(t in normalized_claim for t in ('tru ','khong thuoc','tap doan','hop tac xa'))):
                structural_issues.append(f'Claim {index}: nhóm nhận giao khoán thiếu ngoại lệ của chủ thể trong nguồn')
            for group in groups:
                if group in normalized_claim and group not in source_body:
                    structural_issues.append(f'Claim {index}: nhóm chủ thể nêu trong kết luận không có trong đúng đoạn dẫn')
            if 'to chuc nuoc ngoai' in normalized_claim and 'chuc nang ngoai giao' in source_body and 'chuc nang ngoai giao' not in normalized_claim:
                structural_issues.append(f'Claim {index}: thiếu giới hạn chức năng ngoại giao của chủ thể')
            if re.search(r'\b(cac doi tuong tren|cac truong hop tren|nhu da neu o tren)\b',normalized_claim):
                structural_issues.append(f'Claim {index}: kết luận phải nêu chủ thể/điều kiện độc lập, không phụ thuộc mệnh đề khác')

            historical=[evidence[i] for i in claim.citation_ids if i in evidence and evidence[i].applicability=='historical']
            if historical and claim.kind=='legal_rule':
                # An expired act remains searchable. Applying it after expiry
                # requires a cited, operative transition, not an LLM opinion.
                current_transitions=[evidence[i] for i in claim.citation_ids if i in evidence
                    and evidence[i].applicability=='current' and any(
                        term in normalize(evidence[i].chunk.text) for term in ('chuyen tiep','tiep tuc thuc hien'))
                    and any((old.document.document_number and normalize(old.document.document_number) in normalize(evidence[i].chunk.text))
                        or any(relation.get('type')=='transition' and relation.get('target_id')==old.document.id
                            and relation.get('source_id')==evidence[i].document.id
                            and any(re.match(rf'^Điều {number}(?:\s|$)',evidence[i].chunk.locator,re.IGNORECASE)
                                for number in re.findall(r'Điều\s+(\d+[a-z]?)',relation.get('source_locator') or relation.get('locator') or '',re.IGNORECASE))
                            for relation in (state['release'] or {}).get('relations',[]))
                        for old in historical)]
                disclosed_history=any(term in normalized_claim for term in ('lich su','da het hieu luc','khong con hieu luc','quy dinh cu','truoc khi'))
                requested_history=any(term in normalize(state['request'].message) for term in ('lich su','quy dinh cu','truoc khi','so sanh'))
                if not current_transitions and not (disclosed_history and requested_history):
                    structural_issues.append(f'Claim {index}: văn bản đã hết hiệu lực tại thời điểm hỏi; cần nguồn chuyển tiếp đang áp dụng hoặc giới hạn rõ việc mô tả quy định lịch sử')
            if claim.kind=='applicability' and any(evidence[i].applicability=='future' for i in claim.citation_ids if i in evidence):
                if not any(phrase in normalized_claim for phrase in ('chua co hieu luc', 'chua den ngay co hieu luc')):
                    structural_issues.append(f'Claim {index}: phải nêu rõ văn bản chưa có hiệu lực trong chính claim trước khi kiểm chứng')
                if any(phrase in normalized_claim for phrase in ('duoc boi thuong','duoc ho tro','co quyen','dong/','trieu dong')):
                    structural_issues.append(f'Claim {index}: không dùng nhãn hiệu lực để áp dụng quyền lợi từ văn bản tương lai')
            cited_text=' '.join(evidence[i].chunk.text for i in claim.citation_ids if i in evidence)
            normalized_source=normalize(cited_text)
            prerequisites=re.findall(r'cac truong hop quy dinh tai khoan (\d+) dieu nay duoc .{0,120}?khi co',normalized_source)
            if prerequisites and 'duoc' in normalized_claim:
                for clause in prerequisites:
                    if not re.search(rf'(?:thuoc|truong hop|doi tuong).{{0,80}}khoan {clause}\b|\bkhoan {clause}.{{0,80}}(?:truong hop|doi tuong|thuoc)',normalized_claim):
                        structural_issues.append(f'Claim {index}: các điều kiện thay thế chỉ áp dụng cho trường hợp thuộc khoản {clause}; cần nêu điều kiện về đối tượng trước khi kết luận')
            if ('mot trong cac dieu kien' in normalized_source
                    and any(term in normalized_claim for term in ('con phai co', 'dong thoi phai co', 'tat ca cac dieu kien'))):
                structural_issues.append(f'Claim {index}: nguồn quy định điều kiện thay thế, không chứng minh yêu cầu đồng thời các điều kiện')
            structural_issues.extend(f'Claim {index}: {issue}' for issue in clause_attribution_issues(claim, list(evidence.values())))
            for clause,article in re.findall(r'\bkhoan\s+(\d+)\s+dieu\s+(\d+[a-z]?)\b',normalized_claim):
                reference=f'khoan {clause} dieu {article}'
                # A cross-reference in the cited operative text can prove its
                # own reference. Otherwise a local clause attribution needs
                # the actual numbered clause, not just the article heading or
                # a continuation belonging to another numbered clause.
                if reference in normalized_source:
                    continue
                local=[evidence[i] for i in claim.citation_ids if i in evidence and
                       re.match(rf'^dieu {article}(?:\s|$)',normalize(evidence[i].chunk.locator))]
                if local and not any(re.search(rf'(?<![\d/])\b{clause}\.\s',normalize(e.chunk.text)) for e in local):
                    structural_issues.append(f'Claim {index}: chưa có đoạn khoản {clause} Điều {article} được dẫn để chứng minh số khoản; không thay bằng khoản khác')
            point_pattern=r'\b([a-zđ])\)\s+(.+?)(?=\s+[a-zđ]\)\s|;|$)'
            claimed_points=re.findall(point_pattern,normalized_claim)
            source_points=re.findall(point_pattern,normalized_source)
            if len(claimed_points)>1 and len(source_points)>1:
                def point_body(body):
                    return ' '.join(word for word in re.findall(r'[\w]+',body) if word not in {'de','viec'})
                wrong_points=[]
                for letter,body in claimed_points:
                    prefix=' '.join(point_body(body).split()[:5])
                    if not any(letter==source_letter and prefix in point_body(source_body)
                               for source_letter,source_body in source_points):
                        wrong_points.append(letter)
                if wrong_points and not re.search(r'\bdiem\s+[a-zđ]\)',normalized_claim):
                    # A summary's bare alphabetic enumeration is presentation,
                    # not an inferred statutory point number. Remove misleading
                    # labels while preserving every word/qualification. Explicit
                    # legal point references are never silently rewritten.
                    claim=claim.model_copy(update={'text':re.sub(r'(?<!\w)[a-zđ]\)\s+','',claim.text)})
                    draft.claims[index]=claim
                    normalized_claim=normalize(claim.text)
                    await self.event(state,'verification','Đã bỏ ký hiệu liệt kê không khớp điểm của văn bản; giữ nguyên nội dung để kiểm chứng.',
                        docs=sorted({evidence[i].document.id for i in claim.citation_ids if i in evidence}))
                elif wrong_points:
                    structural_issues.append(f'Claim {index}: ký hiệu điểm {wrong_points[0]}) không khớp nội dung trong nguồn; không thay điểm pháp luật bằng điểm khác')
            references=re.findall(r'\b(?:diem\s+[a-zđ]\s+)?khoan\s+\d+\s+dieu\s+\d+[a-z]?\b',
                                  normalize(state['request'].message)+' '+normalized_claim)
            expanded_claim=re.sub(r'\bubnd\b','uy ban nhan dan',normalized_claim)
            origin=re.search(r'\btu\s+(.+?)\s+(?:sang|cho)\s+',expanded_claim)
            if origin and 'chu tich uy ban nhan dan cap huyen' in origin[1]:
                # A heading can name both the committee and its chair while
                # a numbered clause transfers only the committee's powers.
                blocks=re.split(r'(?=\b\d+\.\s+tham quyen cua\b)',normalized_source)
                for block in blocks:
                    actor=re.match(r'\d+\.\s+tham quyen cua\s+(.+?)\s+(?:theo|chuyen|duoc|quy dinh)\b',block)
                    if (actor and any(reference in block for reference in references)
                            and 'chu tich' not in actor[1]):
                        structural_issues.append(f'Claim {index}: khoản cụ thể chuyển thẩm quyền của UBND cấp huyện, không phải Chủ tịch UBND cấp huyện; tiêu đề chung không chứng minh chủ thể bổ sung')
            number_pattern=r'(?<![\d/])(\d{1,6})/((?:19|20)\d{2})(?!/\d)'
            def act_numbers(text):
                return {f'{int(sequence)}/{year}' for sequence,year in re.findall(number_pattern,text)}
            claimed_numbers=act_numbers(normalized_claim)
            source_numbers=act_numbers(normalized_source)
            source_numbers.update(number for citation_id in claim.citation_ids if citation_id in evidence
                for number in act_numbers(normalize(evidence[citation_id].document.document_number or '')))
            if claimed_numbers-source_numbers:
                structural_issues.append(f'Claim {index}: số văn bản trong kết luận không được đoạn dẫn hoặc metadata nguồn chứng minh')
            if 'bai bo' in normalized_claim:
                for unit in ('khoan','dieu'):
                    extra=re.search(r'\b(?:va|cung)\s+(?:mot so|cac|nhieu)\s+'+unit+r'\b',normalized_claim)
                    named_units=set(re.findall(r'\b'+unit+r'\s+(\d+[a-z]?)\b',normalized_source))
                    if extra and len(named_units)<(1 if unit=='khoan' else 2):
                        structural_issues.append(f'Claim {index}: mở rộng phạm vi bãi bỏ ngoài điều/khoản được nguồn chứng minh')
            generalizations=('thuong dien ra','thuong xay ra','luon dien ra','luon xay ra','moi van ban','tat ca cac van ban')
            if any(phrase in normalized_claim and phrase not in normalized_source for phrase in generalizations):
                structural_issues.append(f'Claim {index}: kết luận tổng quát không được đoạn nguồn hỗ trợ')
            if ('khong ap dung' in normalized_claim and 'ho so' in normalized_claim
                    and any(word in normalized_claim for word in ('truoc','cu'))
                    and not any(word in normalize(cited_text) for word in ('chuyen tiep','phuong an','ho so'))):
                structural_issues.append(f'Claim {index}: mốc hiệu lực không chứng minh cách xử lý mọi hồ sơ cũ; cần căn cứ chuyển tiếp')
            claimed_dates=claim_source_dates(claim.text,state['as_of'])
            if claimed_dates-dates_in(cited_text):
                structural_issues.append(f'Claim {index}: ngày nêu trong kết luận không xuất hiện trong đoạn được dẫn')
            effective_dates = claim_effective_dates(claim.text,state['as_of'])
            if effective_dates and not any(
                    effective_dates <= source_effective_dates(evidence[i].chunk.text)
                    for i in claim.citation_ids if i in evidence):
                structural_issues.append(f'Claim {index}: cần đoạn quy định hiệu lực có đúng ngày, không dùng ngày ban hành')
            if 'chuyen giao cho uy ban nhan dan cap xa' in normalized_claim:
                if any('chuyen giao cho chu tich uy ban nhan dan cap xa' in normalize(evidence[i].chunk.text)
                       for i in claim.citation_ids if i in evidence):
                    structural_issues.append(f'Claim {index}: nhầm Chủ tịch UBND cấp xã với UBND cấp xã')
            # A current assertion from an affected original article must also cite the effective amendment.
            # Clause-level changes never invalidate the whole original document.
            cited_documents = {evidence[i].document.id for i in claim.citation_ids if i in evidence}
            for relation in (state['release'] or {}).get('unresolved_relations', []):
                if relation['target_id'] in cited_documents and relation['type'] in {'amends','repeals','overrides'}:
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
                                         for n in re.findall(r"Điều\s+(\d+[a-z]?)", locator, flags=re.IGNORECASE)]
                    affected = not relation.get('target_locators_complete') or any(re.search(rf"^Điều {n}(?:\s|$)", item.chunk.locator, re.IGNORECASE) for n in affected_articles)
                    if affected and amendment_affects_claim(relation,item,claim) and relation["source_id"] not in cited_documents:
                        structural_issues.append(f"Claim {index}: {item.chunk.locator} có sửa đổi/bãi bỏ một phần bởi {relation['source_id']} ({relation.get('source_locator')}); cần đối chiếu và dẫn phần tác động phù hợp")
        if structural_issues and all(citation in evidence for claim in draft.claims for citation in claim.citation_ids):
            state['verification']=Verification(issues=structural_issues)
            await self.event(state,'verification',f'0/{len(draft.claims)} kết luận được phát hành; lỗi phạm vi/điều kiện đã xác định, không gọi model để phê duyệt lại. '+redact('; '.join(structural_issues[:3]))[:500])
            return state
        cited_ids={citation_id for claim in draft.claims for citation_id in claim.citation_ids}
        selected=[item for item in state['evidence'] if item.chunk.id in cited_ids]
        spans=source_spans(selected)
        verification_context,documents=self.prompt_context(state,cited_ids)
        aliases={item['citation_id']:f'C{index+1}' for index,item in enumerate(verification_context)}
        actual={value:key for key,value in aliases.items()}
        span_aliases={key:f'S{index+1}' for index,key in enumerate(spans)}
        actual_spans={value:key for key,value in span_aliases.items()}
        checked_draft=draft.model_dump()
        checked_draft.pop('summary',None)
        for claim in checked_draft['claims']:
            claim['citation_ids']=[aliases.get(key,key) for key in claim['citation_ids']]
        model_context=[{**item,'citation_id':aliases[item['citation_id']]} for item in verification_context]
        if self.provider.settings.llm_provider == 'groq':
            # source_spans already contain exact overlapping text covering every
            # cited passage; avoid sending that same text twice to the verifier.
            model_context=[{k:v for k,v in item.items() if k!='text'} for item in model_context]
        model_spans=[{**item,'span_id':span_aliases[key],'citation_id':aliases[item['citation_id']]} for key,item in spans.items()]
        checked = await self.provider.generate(Verification,
            "Verify only stated claims against the actual question and as_of, not hypothetical cases. summary is "
            "intentionally absent and never an issue. Support a claim only if every cited passage proves its precise "
            "rule, actor, scope and applicability. A matching source span only proves provenance, not entailment. "
            "All claim indexes are ZERO-BASED. issues contains defects only, each starting Claim <index>:; "
            "never put a positive approval in issues. Check subject, prerequisite, alternative condition, "
            "exception and consequence separately. Reject a claim "
            "that assigns an example to a clause containing different types of facts, even if both examples appear "
            "somewhere in the article. Lists of assistance must not imply automatic entitlement for every household. "
            "Act names/preambles do not prove provisions. Do not replace the "
            "requested clause with another similar one. Record issues for unsupported statements in next_steps or "
            "failure to answer the direct question. Preserve Chủ tịch UBND versus UBND exactly. "
            "Check every stated clause number and point letter against its operative text: an article heading, "
            "a reference to eligible cases, or a continuation of another clause cannot prove the attributed clause. "
            "For every supported index and EVERY citation_id, select one or more supporting_spans by exact span_id "
            "from that citation's source_spans. The server extracts verbatim text: do not invent IDs or paraphrase quotes. "
            "All spans together cover the full cited passage; read continuation spans when one is incomplete. "
            "Do not demand unrelated points of a list when its actor and the relevant point are explicitly proved. "
            "unverified cannot prove current law. historical supports historical/explicit transitional rules. "
            "future supports only kind=applicability saying NOT yet effective plus a source-proven start, never rights. "
            "provision_specific must use the correct clause's dates; never infer whole-article validity. "
            "official_news proves project events/context only, not household or parcel entitlements. "
            "An as_of observation date may be inferred from verified dates/relations; commencement must be in operative text. "
            "Replacement/commencement alone neither excludes all old cases nor requires an unasked private-case conclusion. "
            "If the answer applies an old private case, check the specific transition. overrides is conditional priority "
            "where rules conflict, not repeal of the whole original act. Check effective special policies/transitions "
            "before supporting original rules on prices, deadlines, publicity, assets or assistance. "
            "If the necessary policy or supporting source is absent, exclude that index, set needs_more_evidence and "
            "a targeted followup_query in Vietnamese. Do not invent evidence or treat coverage_gaps as proof.",
            {"question": redact(state["request"].message), "as_of": str(state["as_of"]),"history":state.get('history',[]),
             "draft": checked_draft, "evidence": model_context,'source_spans':model_spans,'documents':documents,
             "coverage_gaps": self.relevant_gaps(state),
             'question_kind':'general_rule' if state.get('general_rule_question') else 'case_or_other',
             "unresolved_relations": self.relevant_unresolved(state)}, state["budget"])
        checked.supporting_quotes=[quote.model_copy(update={'citation_id':actual.get(quote.citation_id,quote.citation_id)})
                                   for quote in checked.supporting_quotes]
        for reference in checked.supporting_spans:
            reference=reference.model_copy(update={'citation_id':actual.get(reference.citation_id,reference.citation_id),
                'span_id':actual_spans.get(reference.span_id,reference.span_id)})
            span=spans.get(reference.span_id)
            if (span and span['citation_id']==reference.citation_id and reference.claim_index<len(draft.claims)
                    and reference.citation_id in draft.claims[reference.claim_index].citation_ids):
                checked.supporting_quotes.append(SupportingQuote(claim_index=reference.claim_index,
                    citation_id=reference.citation_id,quote=span['quote']))
        checked.issues = structural_issues + checked.issues
        for index,claim in enumerate(draft.claims):
            proven = {q.citation_id for q in checked.supporting_quotes if q.claim_index==index
                and q.citation_id in evidence and quote_matches(q.quote,evidence[q.citation_id].chunk.text)}
            if set(claim.citation_ids)-proven:
                checked.issues.append(f'Claim {index}: thiếu trích đoạn nguyên văn chứng minh tại đúng citation_id')
                structural_issues.append(f'Claim {index}: thiếu chứng cứ trích dẫn trực tiếp')
        blocked = {int(match.group(1)) for issue in checked.issues if (match := re.match(r"Claim (\d+):", issue))}
        allowed = {i for i in range(len(draft.claims)) if all(c in evidence for c in draft.claims[i].citation_ids)
                   and i not in blocked and not all(evidence[c].applicability=='unverified' or
                   (evidence[c].applicability=='future' and draft.claims[i].kind!='applicability') for c in draft.claims[i].citation_ids)}
        checked.supported_claim_indexes = sorted(set(checked.supported_claim_indexes) & allowed)
        state["verification"] = checked
        summary=f"{len(checked.supported_claim_indexes)}/{len(draft.claims)} kết luận qua kiểm tra với chứng cứ trong corpus; {len(checked.issues)} vấn đề."
        if checked.issues:
            summary+=' '+redact('; '.join(checked.issues[:3]))[:500]
        await self.event(state, "verification", summary)
        return state

    @staticmethod
    def route(state):
        verification = state["verification"]
        can_retry = (state["rounds"] < 2
                     and state["budget"].llm_calls <= 4 and state['budget'].tool_calls<12)
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
        if len(claims) != len(draft.claims) or check.issues or check.needs_more_evidence:
            # Partial paragraphs can lose the subject or condition they depend on.
            # Global issues and unresolved evidence requests also veto release,
            # even when the verifier contradictorily approves every index.
            claims=[]
        for claim in claims:
            claim.text=re.sub(r'\s*\(C\d+\)', '', claim.text)
        evidence = {e.chunk.id: e for e in state["evidence"]}
        cited_ids = list(dict.fromkeys(i for c in claims for i in c.citation_ids))
        citations = [Citation(id=i, document_id=evidence[i].document.id, title=evidence[i].document.title,
                              document_number=evidence[i].document.document_number, url=str(evidence[i].document.url),
                              locator=evidence[i].chunk.locator, excerpt=evidence[i].chunk.text,
                              checked_at=evidence[i].document.checked_at, applicability=evidence[i].applicability,
                              source_review_notes=evidence[i].document.source_review_notes,
                              page=evidence[i].chunk.page, source_url=citation_source_url(evidence[i])) for i in cited_ids]
        status = draft.status
        if len(claims) != len(draft.claims) or check.issues or check.needs_more_evidence:
            status = "insufficient_evidence"
        if status == "answered" and not claims:
            status = "insufficient_evidence"
        release = state["release"]
        stale = False
        if release:
            checked_at = datetime.fromisoformat(release["checked_at"].replace("Z", "+00:00"))
            stale = not await asyncio.to_thread(self.store.source_fresh, release, {evidence[i].document.id for c in claims for i in c.citation_ids} if claims else None)
        if stale and state["as_of"] >= local_date():
            status = "insufficient_evidence"
            claims, citations = [], []
        outside=state['plan'].out_of_scope or draft.out_of_scope
        if outside:
            status='insufficient_evidence'
            claims,citations=[],[]
        # Only verified content is rendered. Never pass unchecked summary/next_steps on a failed verification.
        # Summary prose is never treated as an unchecked place to smuggle legal assertions.
        intro = {"answered": "Đã đối chiếu các căn cứ dưới đây.",
                 "clarification_needed": "Cần bổ sung dữ kiện để xác định quy định áp dụng cho hồ sơ cụ thể.",
                 "insufficient_evidence": "Chưa có đủ chứng cứ đã xác minh để kết luận đầy đủ."}[status]
        if stale and state["as_of"] >= local_date():
            intro = "Bộ dữ liệu đã quá bảy ngày chưa được kiểm tra nguồn; chưa thể xác nhận quy định hiện hành."
        content = intro
        if state.get('unsupported_references'):
            content='Chưa có văn bản mang số '+', '.join(state['unsupported_references'])+' đã được kiểm chứng trong corpus. Chưa thể xác nhận nội dung, mức tiền hoặc quyền lợi được viện dẫn; cần đối chiếu nguồn văn bản chính thức. Không suy ra văn bản có hay không tồn tại chỉ từ việc thiếu trong corpus.'
        if state.get('freshness_question'):
            content='Không thể bảo đảm tính hiện hành chỉ từ dữ liệu chưa được kiểm tra lại. '
            content+='Nếu quá bảy ngày chưa kiểm tra nguồn thành công, cần nêu giới hạn cập nhật và đối chiếu văn bản chính thức, mốc hiệu lực, sửa đổi và chuyển tiếp trước khi kết luận. '
            content+=('Corpus thực tế đã quá bảy ngày chưa kiểm tra nguồn.' if stale else
                      'Giả định dữ liệu cũ trong câu hỏi không có nghĩa corpus thực tế đã quá hạn; mốc kiểm tra được ghi bên dưới.')
        if state.get('place_clarification'):
            content='Tên huyện cũ chưa đủ để ánh xạ tới một xã/phường mới hoặc xác định một thửa đất thuộc dự án. Cần đối chiếu địa bàn chi tiết và ranh giới/hồ sơ thu hồi.'
        if outside:
            content=('Hệ thống chỉ hỗ trợ Vành đai 4 tại Hà Nội; không có dữ liệu dự án khác.' if state.get('unsupported_project') else 'Câu hỏi nằm ngoài phạm vi pháp luật đất đai và quy hoạch Hà Nội.')
        if claims:
            content += "\n\n" + "\n\n".join(c.text + " " + " ".join(f"[{cited_ids.index(i)+1}]" for i in c.citation_ids) for c in claims)
        missing = public_missing_facts(state["plan"].missing_facts + draft.missing_facts,release)
        if state.get('general_rule_question'):missing=[]
        if outside:missing=[]
        if missing and status == "answered":
            status = "clarification_needed"
            content = content.replace("Đã đối chiếu các căn cứ dưới đây.", "Cần bổ sung dữ kiện để xác định quy định áp dụng cho hồ sơ cụ thể.", 1)
        if missing:
            content += "\n\nThông tin cần bổ sung:\n" + "\n".join(f"- {x}" for x in missing)
        historical_question = state['as_of'] < date(2026,4,2) and any(number in normalize(state['request'].message)
            for number in ('40/2026','56/2024'))
        if historical_question and any(g['document_id']=='qd-56-2024-hanoi' for g in (release or {}).get('coverage_gaps',[])):
            content+='\n\nBộ dữ liệu chưa có toàn văn đạt kiểm tra của QĐ56/2024; chưa thể xác định đầy đủ quyền lợi hồ sơ lịch sử phụ thuộc văn bản này.'
        if draft.next_steps and not check.issues and not check.needs_more_evidence and not outside:
            content += "\n\nBước tiếp theo:\n" + "\n".join(f"- {x}" for x in draft.next_steps)
        content += f"\n\nThời điểm xem xét: {state['as_of'].strftime('%d/%m/%Y')}."
        if release:
            content += f" Dữ liệu được kiểm tra: {release['checked_at'][:10]}."
        budget = state["budget"]
        state["result"] = ChatResult(status=status, content=content, citations=citations, verified_claims=claims, as_of=state["as_of"],
            corpus_release=(release or {}).get("id"), trace_id=str(uuid.uuid4()), trace=state["trace"], missing_facts=missing,
            llm_calls=budget.llm_calls, tool_calls=budget.tool_calls, token_usage=budget.tokens,
            embedding_calls=budget.embedding_calls,
            elapsed_ms=int((time.monotonic()-budget.started)*1000), model=self.provider.settings.generation_model,
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
                raise ProviderUnavailable("API key của provider được chọn chưa được cấu hình; không sinh câu trả lời giả")
            async with asyncio.timeout(self.provider.settings.turn_timeout_seconds):
                state["release"] = await asyncio.to_thread(self.store.release, release_id, True)
                # Client history is untrusted context, never legal evidence.
                known={d['id']:d for d in (state['release'] or {}).get('documents',[])}
                state['history']=[{'role':item.role,'content':redact(item.content),
                    'as_of':str(item.as_of) if item.as_of else None,
                    'citations':[{'document_id':c.document_id,
                        'document_number':known[c.document_id].get('document_number'), 'locator':c.locator}
                        for c in item.citations if c.document_id in known]}
                    for item in request.history]
                if state['as_of'] >= local_date() and not await asyncio.to_thread(self.store.source_fresh, state['release'] or {}):
                    state['result']=ChatResult(**public_status(state['release']),status='insufficient_evidence',
                        content='Nguồn đã quá bảy ngày chưa được kiểm tra lại; chưa thể xác nhận quy định hiện hành. Có thể xem snapshot trong thư viện nguồn.',
                        as_of=state['as_of'],corpus_release=(state['release'] or {}).get('id'),trace_id=str(uuid.uuid4()),
                        model=self.provider.settings.generation_model,embedding_model=self.provider.settings.embedding_model,
                        mode=request.mode)
                    return state['result']
                output = await self.graph.ainvoke(state, config={"recursion_limit": 16})
                return output["result"]
        except (ProviderUnavailable, RateLimited, BudgetExceeded, TimeoutError) as exc:
            status = "limited" if isinstance(exc, (RateLimited, BudgetExceeded)) else "error"
            content = (f"Nhà cung cấp AI đang giới hạn request. Vui lòng thử lại sau {exc.retry_after} giây."
                       if isinstance(exc,RateLimited) else "Lượt hỏi đã đạt giới hạn thực thi. Hãy tách câu hỏi hoặc thử lại."
                       if isinstance(exc,BudgetExceeded) else (
                "Lượt hỏi đã quá thời gian xử lý. Vui lòng thử lại." if isinstance(exc, TimeoutError) else str(exc))
                       )
            publication = await asyncio.to_thread(self.store.publication, (state['release'] or {}).get('id'))
            return ChatResult(**public_status(state['release'], publication), status=status, content=content, as_of=state["as_of"],
                corpus_release=(state["release"] or {}).get("id"), trace_id=str(uuid.uuid4()), trace=state["trace"],
                llm_calls=budget.llm_calls, tool_calls=budget.tool_calls, token_usage=budget.tokens,
                embedding_calls=budget.embedding_calls,
                elapsed_ms=int((time.monotonic()-budget.started)*1000), model=self.provider.settings.generation_model,
                embedding_model=(state['release'] or {}).get('embedding_model', self.provider.settings.embedding_model), mode=request.mode,
                retry_after=exc.retry_after if isinstance(exc, RateLimited) else None)
