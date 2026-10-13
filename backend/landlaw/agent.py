import asyncio
import json
import re
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from .models import ChatRequest, ChatResult, Citation, Document, Draft, Evidence, Relation, TraceEvent
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


def claim_effective_dates(text):
    """Commencement/expiry dates, excluding an act's separately stated issue date."""
    pattern = (r'hieu luc(?:\s+thi hanh)?\s+(?:(?:ke tu|tu|vao|den)\s+)?(?:ngay\s+)?'
               r'(\d{1,2}(?:[/-]\d{1,2}[/-]\d{4}|\s+thang\s+\d{1,2}\s+nam\s+\d{4}))')
    return {value for match in re.finditer(pattern, normalize(text)) for value in dates_in('ngay ' + match[1])}


def public_missing_facts(facts,release):
    known=['/'.join(normalize(d.get('document_number') or '').split('/')[:2])
        for d in (release or {}).get('documents',[]) if d.get('issued_on')]
    return list(dict.fromkeys(fact for fact in facts
        if not any(key in fact.lower() for key in ('document_id','citation_id'))
        and not ('ngay ban hanh' in normalize(fact)
            and any(number and number in normalize(fact) for number in known))))


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
        question=normalize(request.message)
        literal_numbers=set(re.findall(r'(?<![\d/])\d{1,6}/(?:19|20)\d{2}(?!/\d)',question))
        known_numbers={'/'.join(normalize(d.get('document_number') or '').split('/')[:2])
                       for d in (state['release'] or {}).get('documents',[])}
        direct_effectivity=(len(literal_numbers)==1 and literal_numbers<=known_numbers
            and any(term in question for term in ('hieu luc','van ban nao thay the','kiem tra mau thuan'))
            and not any(term in question for term in ('ho so','quyen loi','tinh tien','tinh boi thuong')))
        if request.mode == "baseline":
            prior = next((m['content'] for m in reversed(state['history']) if m['role']=='user'), '')
            # Baseline also receives the same conversational context; no planner call.
            query = (prior[:500]+' '+request.message) if prior else request.message
            state["plan"] = Plan(tools=[ToolCall(name="search_law", query=query[:1000])])
        elif direct_effectivity:
            state['plan']=Plan(tools=[ToolCall(name='search_law',query=request.message[:1000])])
            await self.event(state,'routing','Đã nhận diện số văn bản và yêu cầu kiểm tra hiệu lực; dùng tra cứu trực tiếp.',
                             'search_law')
        else:
            catalogue=self.catalogue(state['release'])
            catalogue_fields=None
            if self.provider.settings.llm_provider=='groq':
                catalogue_fields=['id','document_number','title','project','effective_from','effective_to']
                catalogue=[[d['id'],d['document_number'],d['title'][:120],d['project'],
                            d['effective_from'],d['effective_to']] for d in catalogue]
            state["plan"] = await self.provider.generate(Plan,
                "Chọn tối đa 3 công cụ chỉ đọc để lấy chứng cứ. search_law tìm luật; search_project tìm hồ sơ dự án; "
                "check_effectivity kiểm tra văn bản theo document_id đã biết; open_article mở điều khoản đã biết; "
                "normalize_place tìm tên địa bàn theo danh mục. Với câu hỏi quyền lợi cá nhân, liệt kê dữ kiện thiếu. "
                "Chỉ đánh dấu out_of_scope khi không liên quan đất đai/quy hoạch Hà Nội. "
                "Câu hỏi quy định chung không cần dựng hồ sơ cá nhân. missing_facts chỉ là dữ kiện riêng "
                "của hồ sơ cần kết luận: loại đất, giấy tờ, ngày quyết định hoặc phê duyệt phương án. "
                "Không yêu cầu người dùng cung cấp nội dung pháp luật, điều kiện do luật quy định "
                "hoặc thông tin văn bản đã có trong catalogue; hệ thống phải tự tra cứu chúng. "
                "Không đoán document_id; khi chưa biết dùng search_law. Câu hỏi đơn giản về một văn bản ưu tiên một công cụ. "
                "Văn bản trong coverage_gaps không mở được; dùng search_law để tìm văn bản tác động có trong corpus.",
                {"question": redact(request.message), "project": request.project, "as_of": str(state["as_of"]),
                 "history": state["history"], "catalogue": catalogue, 'catalogue_fields':catalogue_fields,
                 "coverage_gaps":(state['release'] or {}).get('coverage_gaps',[])}, state["budget"])
            # Internal identifiers and dates already available in the source
            # catalogue are tool inputs, not facts a citizen must supply.
            state['plan'].missing_facts=public_missing_facts(state['plan'].missing_facts,state['release'])
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
                                      (state["release"] or {}).get("id"), (state['release'] or {}).get('embedding_model', self.provider.settings.embedding_model))
        # An explicitly requested missing historical document can still have a
        # verified replacement. Open that operative clause before generic hits.
        release = state['release'] or {}
        requested = {g['document_id'] for g in release.get('coverage_gaps', [])
                   if normalize(g.get('document_number', '')).split('/qd')[0] in normalize(query)
                   and g.get('document_number')}
        requested.update(d['id'] for d in release.get('documents',[]) if d.get('document_number')
            and normalize(d['document_number']).split('/qd')[0] in normalize(query))
        priority = {}
        for relation in release.get('relations', []) + release.get('unresolved_relations', []):
            if relation['target_id'] in requested and relation['type'] == 'replaces' and state['budget'].tool_calls < 12:
                state['budget'].tool()
                doc = await asyncio.to_thread(self.store.open_document, relation['source_id'], release['id'],
                                             relation.get('source_locator') or relation.get('locator'))
                if doc:
                    for chunk in doc.chunks:
                        priority[chunk.id] = Evidence(chunk=chunk, document=doc)
        for hit in hits:
            priority.setdefault(hit.chunk.id, hit)
        return list(priority.values())[:8]

    async def tools(self, state):
        if state["plan"].out_of_scope or not state["release"]:
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
                state["tool_notes"].append({"tool": call.name, "matches": matched[:6]})
                await self.event(state, "tool", f"Tìm thấy {len(matched)} ánh xạ địa bàn có nguồn; thiếu ánh xạ thì cần hỏi lại.", call.name)
            for item in results:
                item.applicability = applicability(item.document, state["as_of"],item.chunk)
                found[item.chunk.id] = item
            await self.event(state, "tool", f"Thu được {len(results)} đoạn chứng cứ.", call.name,
                             sorted({e.document.id for e in results}))
        # Follow legal relationships; deterministic scope checks are never delegated entirely to the LLM.
        catalogue = {d['id']: d for d in state['release']['documents']}
        opened = set()
        for doc_id in list(dict.fromkeys(e.document.id for e in found.values()))[:4]:
            if state["budget"].tool_calls >= 12:
                break
            state["budget"].tool()
            relations = await asyncio.to_thread(self.store.relations, doc_id, release_id)
            relations = [relation for relation in relations
                         if relation_may_affect(relation, doc_id, list(found.values()))]
            relations.sort(key=lambda relation: (
                relation.target_id == doc_id,
                catalogue.get(relation.source_id, {}).get('effective_from') or ''), reverse=True)
            for relation in relations:
                if state['budget'].tool_calls >= 12:
                    break
                if relation.source_id==doc_id and relation.source_locator and state['budget'].tool_calls<12:
                    numbers=re.findall(r'Điều\s+(\d+)',relation.source_locator)
                    if not any(e.document.id==doc_id and any(e.chunk.locator==f'Điều {n}' for n in numbers) for e in found.values()):
                        state['budget'].tool()
                        source=await asyncio.to_thread(self.store.open_document,doc_id,release_id,relation.source_locator,state['request'].message)
                        if source:
                            for chunk in source.chunks:
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
                doc = await asyncio.to_thread(self.store.open_document, related_id, release_id, locator,state['request'].message)
                if doc:
                    for chunk in relation_chunks(doc, locator):
                        found.setdefault(chunk.id, Evidence(chunk=chunk, document=doc,
                                                           applicability=applicability(doc, state["as_of"],chunk)))
                    await self.event(state, 'tool', 'Đã mở văn bản có quan hệ pháp lý để đối chiếu phạm vi.',
                                     'open_article', [related_id])
            await self.event(state, "applicability", f"Đã kiểm tra {len(relations)} quan hệ pháp lý theo thời điểm.", "check_effectivity", [doc_id])
        for item in previous_evidence:
            found.setdefault(item.chunk.id,item)
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
                 'document_number':e.document.document_number,'page':e.chunk.page,
                 "kind": e.document.source_kind, "locator": e.chunk.locator, "text": e.chunk.text,
                 "applicability": e.applicability, "effective_from": str(e.document.effective_from),
                 "effective_to": str(e.document.effective_to),
                 "provision_validity": e.document.provision_validity,
                 'source_review_notes':e.document.source_review_notes,
                 "legal_relations": self.relation_context(e, state)} for e in state["evidence"]]

    def prompt_context(self,state,selected_ids=None):
        """Send each document's legal relationships once, preserving every passage.

        Repeating a long amendment graph for each chunk can overflow a free
        model's context and distract from the actual operative text.
        """
        passages,documents=[],{}
        candidates=self.context(state)
        if self.provider.settings.llm_provider=='groq' and selected_ids is None:
            question=normalize(state['request'].message) if state.get('request') else ''
            numbers=set(re.findall(r'(?<![\d/])\d{1,6}/(?:19|20)\d{2}(?!/\d)',question))
            articles=set(re.findall(r'\bdieu\s+(\d+[a-z]?)\b',question))
            terms=set(re.findall(r'[a-z0-9]{3,}',question))-{'quyet','dinh','dieu','ngay','theo','khong','van','ban','toi'}
            temporal=any(term in question for term in ('hieu luc','thay the','bai bo','ap dung ngay'))
            def relevant(item):
                body=normalize(item['text']);locator=normalize(item['locator'])
                exact_article=any(re.match(rf'^dieu {n}(?:\s|$)',locator) for n in articles)
                body_numbers=sum(n in body for n in numbers)
                document_match=any(n in normalize(item.get('document_number') or '') for n in numbers)
                operative=temporal and any(term in body for term in ('co hieu luc','thay the','bai bo'))
                overlap=len(terms & set(body.split()))/max(1,len(body.split()))**.5
                return (exact_article and (document_match or not numbers),body_numbers,operative,document_match,overlap)
            candidates=sorted(candidates,key=relevant,reverse=True)
        for item in candidates:
            if selected_ids is not None and item['citation_id'] not in selected_ids:
                continue
            document_id=item['document_id']
            documents.setdefault(document_id,{key:item[key] for key in (
                'document_id','title','document_number','kind','effective_from','effective_to',
                'provision_validity','legal_relations','source_review_notes')})
            passage={key:item[key] for key in (
                'citation_id','document_id','page','locator','text','applicability')}
            if self.provider.settings.llm_provider=='groq' and selected_ids is None:
                # Select whole passages rather than truncating clauses. Retrieval
                # still retains eight primary hits and related evidence in trace.
                projected_docs={k:v for k,v in documents.items()
                                if k in {p['document_id'] for p in passages} | {document_id}}
                if len(json.dumps([passages+[passage],list(projected_docs.values())],ensure_ascii=False))>7000:
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
        if state["plan"].out_of_scope:
            state["draft"] = Draft(status="insufficient_evidence", summary="Câu hỏi nằm ngoài phạm vi đất đai và quy hoạch Hà Nội.",out_of_scope=True)
        elif not state["evidence"]:
            state["draft"] = Draft(status="insufficient_evidence", summary="Chưa tìm được chứng cứ trong bộ dữ liệu đã công bố.",
                                   missing_facts=state["plan"].missing_facts)
        else:
            contexts,documents=self.prompt_context(state)
            aliases={item['citation_id']:f'C{index+1}' for index,item in enumerate(contexts)}
            contexts=[{**item,'citation_id':aliases[item['citation_id']]} for item in contexts]
            state["draft"] = await self.provider.generate(Draft,
                "Tạo câu trả lời có cấu trúc. summary chỉ giới thiệu kết quả và giới hạn, không chứa kết luận pháp lý "
                "không dẫn nguồn. MỌI kết luận pháp lý nằm trong claims, gắn citation_ids có trong evidence. "
                "Đoạn unverified/future không chứng minh quy định hiện hành. historical chỉ dùng khi giải thích lịch sử "
                "provision_specific có mốc riêng tại khoản được ghi; phải kiểm tra đúng khoản và không suy hiệu lực toàn điều. "
                "hoặc chuyển tiếp được chứng minh. Không coi official_news là quy phạm. Nếu thiếu dữ kiện hồ sơ, "
                "dùng clarification_needed. Không kết luận chắc chắn về quyền lợi hộ/thửa hoặc số tiền. "
                "Nếu hỏi quy định chung, trả lời answered khi có đủ chứng cứ để giải thích điều kiện; "
                "không tự chuyển thành hỏi hồ sơ cá nhân hoặc yêu cầu người dùng cung cấp quy định pháp luật. "
                "Đánh dấu out_of_scope nếu câu hỏi không thuộc pháp luật đất đai/quy hoạch Hà Nội; không tư vấn y tế, đầu tư hoặc lĩnh vực ngoài phạm vi. "
                "next_steps chỉ là hướng dẫn đối chiếu hồ sơ chung; thời hạn/điều kiện pháp lý phải đưa vào claims có nguồn. "
                "coverage_gaps và unresolved_relations chỉ mô tả phần còn thiếu, không phải chứng cứ. "
                "Không khẳng định quyền lợi lịch sử theo QĐ56/2024 khi thiếu toàn văn; không suy nội dung văn bản cũ "
                "từ văn bản thay thế. Khi câu hỏi phụ thuộc phần thiếu, trả lời có giới hạn và chỉ rõ tài liệu cần đối chiếu. "
                "Giữ đúng chủ thể: Chủ tịch UBND khác UBND; không rút gọn làm đổi thẩm quyền. "
                "kind=applicability chỉ để nêu mốc hiệu lực/tình trạng áp dụng, không chứa quyền lợi. "
                "Có thể dẫn đoạn future để giải thích văn bản CHƯA có hiệu lực, không áp dụng quyền lợi từ đó. "
                "kind=context chỉ cho bối cảnh dự án. Trả lời trực tiếp vấn đề được hỏi trước khi giải thích bổ sung. "
                "Không thêm ngày hiệu lực nếu câu hỏi không yêu cầu. Nếu nêu ngày hiệu lực, phải dẫn đúng đoạn "
                "quy định hiệu lực và chứa ngày đó; metadata ngày ban hành không chứng minh ngày hiệu lực. "
                "Ưu tiên ít claims rõ ràng, mỗi claim dẫn đoạn chứng minh trực tiếp; không ghép thêm căn cứ không cần thiết. "
                "Tối đa ba claims, không lặp lại cùng kết luận. Ngày có hiệu lực chỉ chứng minh mốc bắt đầu, "
                "không chứng minh mọi hồ sơ cũ đều bị loại hay tự động chuyển sang chính sách mới. "
                "Kết luận về áp dụng hồ sơ cũ cần điều khoản chuyển tiếp cụ thể; nếu chưa có, hỏi ngày quyết định "
                "thu hồi, ngày duyệt phương án và nêu chưa xác định quyền lợi của hồ sơ. "
                "citation_ids chỉ được chọn mã C1, C2,... có trong allowed_citation_ids; không tạo mã hoặc dùng document_id. "
                "Câu hỏi chỉ về hiệu lực/thay thế một văn bản nên có một hoặc hai claims, kind=applicability, không lặp các mốc ở nhiều claims.",
                {"question": redact(state["request"].message), "as_of": str(state["as_of"]), "history": state["history"],
                 "missing_facts": state["plan"].missing_facts, "tool_results": state["tool_notes"], "evidence": contexts,
                 "documents":documents,
                 'allowed_citation_ids':list(aliases.values()),
                 "coverage_gaps": (state['release'] or {}).get('coverage_gaps', []),
                 "unresolved_relations": (state['release'] or {}).get('unresolved_relations', []),
                 'context_selection':{'complete_passages':len(contexts),'retrieved_candidates':len(state['evidence']),
                                      'omitted_candidates_are_not_citable':True},
                 "previous_issues": state.get("verification", Verification()).issues}, state["budget"])
            actual={value:key for key,value in aliases.items()}
            state['draft'].claims=[claim.model_copy(update={'citation_ids':[actual.get(key,key) for key in claim.citation_ids]})
                                   for claim in state['draft'].claims]
        await self.event(state, "synthesis", "Đã tạo bản trả lời; đang kiểm tra trước khi hiển thị.")
        return state

    async def verify(self, state):
        draft = state["draft"]
        if not state["evidence"]:
            state["verification"] = Verification()
            return state
        evidence = {e.chunk.id: e for e in state["evidence"]}
        repaired=[]
        for index,claim in enumerate(draft.claims):
            claim_dates=claim_effective_dates(claim.text)
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
            if claim.kind=='applicability' and any(evidence[i].applicability=='future' for i in claim.citation_ids if i in evidence):
                if any(phrase in normalized_claim for phrase in ('duoc boi thuong','duoc ho tro','co quyen','dong/','trieu dong')):
                    structural_issues.append(f'Claim {index}: không dùng nhãn hiệu lực để áp dụng quyền lợi từ văn bản tương lai')
            cited_text=' '.join(evidence[i].chunk.text for i in claim.citation_ids if i in evidence)
            if ('khong ap dung' in normalized_claim and 'ho so' in normalized_claim
                    and any(word in normalized_claim for word in ('truoc','cu'))
                    and not any(word in normalize(cited_text) for word in ('chuyen tiep','phuong an','ho so'))):
                structural_issues.append(f'Claim {index}: mốc hiệu lực không chứng minh cách xử lý mọi hồ sơ cũ; cần căn cứ chuyển tiếp')
            claimed_dates=claim_source_dates(claim.text,state['as_of'])
            if claimed_dates-dates_in(cited_text):
                structural_issues.append(f'Claim {index}: ngày nêu trong kết luận không xuất hiện trong đoạn được dẫn')
            effective_dates = claim_effective_dates(claim.text)
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
                    if affected and relation["source_id"] not in cited_documents:
                        structural_issues.append(f"Claim {index}: điều khoản có sửa đổi/bãi bỏ một phần; cần dẫn cả văn bản tác động")
        cited_ids={citation_id for claim in draft.claims for citation_id in claim.citation_ids}
        selected=[item for item in state['evidence'] if item.chunk.id in cited_ids]
        spans=source_spans(selected)
        verification_context,documents=self.prompt_context(state,cited_ids)
        aliases={item['citation_id']:f'C{index+1}' for index,item in enumerate(verification_context)}
        actual={value:key for key,value in aliases.items()}
        span_aliases={key:f'S{index+1}' for index,key in enumerate(spans)}
        actual_spans={value:key for key,value in span_aliases.items()}
        checked_draft=draft.model_dump()
        for claim in checked_draft['claims']:
            claim['citation_ids']=[aliases.get(key,key) for key in claim['citation_ids']]
        model_context=[{**item,'citation_id':aliases[item['citation_id']]} for item in verification_context]
        if self.provider.settings.llm_provider=='groq':
            # source_spans already contain exact overlapping text covering every
            # cited passage; avoid sending that same text twice to the verifier.
            model_context=[{k:v for k,v in item.items() if k!='text'} for item in model_context]
        model_spans=[{**item,'span_id':span_aliases[key],'citation_id':aliases[item['citation_id']]} for key,item in spans.items()]
        checked = await self.provider.generate(Verification,
            "You are an evidence verifier. For EVERY supported claim, select supporting_spans using span_id "
            "from source_spans that actually proves that claim and every citation_id. Never invent a span_id. "
            "The server extracts its exact original source text; do not paraphrase it as a quote. "
            "Do not confirm a claim if the selected span only names a law or fails to prove the asserted rule. "
            "You may alternatively return supporting_quotes, but quote MUST be copied verbatim from evidence.text, "
            "never from draft.claims.text. An as_of observation date can be inferred from verified effectivity "
            "dates and relationships; an asserted commencement date must appear in the operative source. "
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
            "trả supporting_spans gồm claim_index, citation_id, span_id từ source_spans của chính citation đó. "
            "Span phải chứng minh nội dung claim tương ứng; đoạn mở đầu/căn cứ tên văn bản không chứng minh điều khoản ở trang khác. "
            "Ngày hiệu lực không chứng minh mọi hồ sơ được xử lý trước đó đều bị loại; cần điều khoản chuyển tiếp "
            "để xác nhận cách xử lý hồ sơ cũ, không suy đoán từ metadata hoặc mốc bắt đầu. "
            "Quan hệ overrides là cơ chế ưu tiên có điều kiện khi cùng vấn đề có quy định khác nhau, "
            "không phải bãi bỏ toàn bộ luật gốc. Đối chiếu nội dung chính sách đang có hiệu lực và chuyển tiếp "
            "trước khi xác nhận quy định gốc về giá đất, thời hạn, công khai, tài sản hoặc hỗ trợ. "
            "Nếu chưa có đoạn chính sách cần thiết để giải quyết khác biệt, yêu cầu truy xuất bổ sung; "
            "không mặc định bản gốc chứng minh đầy đủ quy định hiện hành. "
            "Không có span chứng minh thì bỏ index và yêu cầu truy xuất bổ sung. Nếu đáp án bỏ sót câu hỏi trực tiếp, ghi issues để sửa.",
            {"question": redact(state["request"].message), "as_of": str(state["as_of"]),
             "draft": checked_draft, "evidence": model_context,'source_spans':model_spans,'documents':documents,
             "coverage_gaps": (state['release'] or {}).get('coverage_gaps', []),
             "unresolved_relations": (state['release'] or {}).get('unresolved_relations', [])}, state["budget"])
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
        blocked = {int(match.group(1)) for issue in structural_issues if (match := re.match(r"Claim (\d+):", issue))}
        allowed = {i for i in range(len(draft.claims)) if all(c in evidence for c in draft.claims[i].citation_ids)
                   and i not in blocked and not all(evidence[c].applicability=='unverified' or
                   (evidence[c].applicability=='future' and draft.claims[i].kind!='applicability') for c in draft.claims[i].citation_ids)}
        checked.supported_claim_indexes = sorted(set(checked.supported_claim_indexes) & allowed)
        state["verification"] = checked
        summary=f"{len(checked.supported_claim_indexes)}/{len(draft.claims)} kết luận được hỗ trợ; {len(checked.issues)} vấn đề."
        if checked.issues:
            summary+=' '+redact('; '.join(checked.issues[:3]))[:500]
        await self.event(state, "verification", summary)
        return state

    @staticmethod
    def route(state):
        verification = state["verification"]
        can_retry = (state["request"].mode == "agentic" and state["rounds"] < 2
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
        evidence = {e.chunk.id: e for e in state["evidence"]}
        for index,claim in enumerate(claims):
            if claim.kind=='applicability' and all(evidence[i].applicability=='future' for i in claim.citation_ids):
                claims[index]=claim.model_copy(update={'text':claim.text+f" Văn bản này chưa có hiệu lực tại ngày {state['as_of'].strftime('%d/%m/%Y')}."})
        cited_ids = list(dict.fromkeys(i for c in claims for i in c.citation_ids))
        citations = [Citation(id=i, document_id=evidence[i].document.id, title=evidence[i].document.title,
                              document_number=evidence[i].document.document_number, url=str(evidence[i].document.url),
                              locator=evidence[i].chunk.locator, excerpt=evidence[i].chunk.text,
                              checked_at=evidence[i].document.checked_at, applicability=evidence[i].applicability,
                              source_review_notes=evidence[i].document.source_review_notes,
                              page=evidence[i].chunk.page, source_url=citation_source_url(evidence[i])) for i in cited_ids]
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
        if outside:
            content='Câu hỏi nằm ngoài phạm vi pháp luật đất đai và quy hoạch Hà Nội.'
        if claims:
            content += "\n\n" + "\n\n".join(c.text + " " + " ".join(f"[{cited_ids.index(i)+1}]" for i in c.citation_ids) for c in claims)
        missing = public_missing_facts(state["plan"].missing_facts + draft.missing_facts,release)
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
        if draft.next_steps and not check.issues and not outside:
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
