from datetime import date, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, model_validator

ProjectID = Literal["ring4", "songhong", "olympic"]
Status = Literal["answered", "clarification_needed", "insufficient_evidence", "limited", "error"]
CitizenIntent = Literal['orientation', 'explain_document', 'prepare_documents', 'understand_benefit',
                        'find_contact', 'disagreement', 'explain_term']


class Interaction(BaseModel):
    """Untrusted UI hints, never evidence or an entitlement decision."""
    intent: CitizenIntent | None = None
    stage: Literal['unknown', 'paper_received', 'inventory', 'proposal', 'moving', 'disagreement'] | None = None


class Clarification(BaseModel):
    fact: Literal['document_type', 'stage', 'place', 'date', 'land_type']
    question: str = Field(min_length=1, max_length=400)
    options: list[str] = Field(default_factory=list, max_length=3)
    allow_unknown: bool = True


class AnswerSection(BaseModel):
    kind: Literal['direct', 'explanation', 'actions']
    claim_indexes: list[int] = Field(min_length=1, max_length=10)


class Chunk(BaseModel):
    id: str
    document_id: str
    text: str
    locator: str
    page: int | None = None
    parent_id: str | None = None
    embedding: list[float] | None = Field(default=None, exclude=True)
    embedding_model: str | None = None
    checksum: str


class SourceFile(BaseModel):
    url: HttpUrl
    checksum: str
    first_page_index: int = Field(ge=0)
    last_page_index: int = Field(ge=0)

    @model_validator(mode='after')
    def ordered_page_range(self):
        if self.last_page_index < self.first_page_index:
            raise ValueError('Source page range is reversed')
        return self


class SourcePage(BaseModel):
    page_index: int = Field(ge=0)
    url: HttpUrl
    checksum: str = Field(pattern=r'^[0-9a-f]{64}$')


class Document(BaseModel):
    id: str
    title: str
    url: HttpUrl
    publication_url: HttpUrl | None = None
    source_kind: Literal["legal", "project_decision", "official_news", "official_procedure", "official_directory"]
    document_number: str | None = None
    issuer: str | None = None
    jurisdiction: str = "Hanoi"
    project: ProjectID | None = None
    topics: list[str] = Field(default_factory=list)
    issued_on: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    applicability_verified: bool = False
    provision_validity: list[dict] = Field(default_factory=list)
    checked_at: datetime
    checksum: str
    source_review_notes: str = ''
    task_tags: list[CitizenIntent] = Field(default_factory=list, max_length=7)
    administrative_scope: str | None = Field(default=None, max_length=200)
    procedure_id: str | None = Field(default=None, max_length=160)
    required_dependency_ids: list[str] = Field(default_factory=list, max_length=20)
    operational_reviewed_at: datetime | None = None
    operational_review_status: Literal['pending', 'unchanged', 'changed', 'unavailable'] = 'pending'
    source_files: list[SourceFile] = Field(default_factory=list)
    source_pages: list[SourcePage] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)


class Relation(BaseModel):
    source_id: str
    target_id: str
    type: Literal["amends", "replaces", "repeals", "guides", "transition", "overrides"]
    locator: str | None = None
    source_locator: str | None = None
    target_locators: list[str] = Field(default_factory=list)
    target_locators_complete: bool = False
    source_url: HttpUrl
    explanation: str


class Evidence(BaseModel):
    chunk: Chunk
    document: Document
    score: float = 0
    applicability: Literal["current", "historical", "future", "unverified", "context", "provision_specific"] = "unverified"


class Citation(BaseModel):
    id: str
    document_id: str
    title: str
    document_number: str | None = None
    url: str
    locator: str
    excerpt: str
    checked_at: datetime
    applicability: str
    source_review_notes: str = ''
    source_kind: str = 'legal'
    page: int | None = None
    source_url: str | None = None


class TraceEvent(BaseModel):
    step: str
    tool: str | None = None
    summary: str
    document_ids: list[str] = Field(default_factory=list)
    elapsed_ms: int = 0


class HistoryCitation(BaseModel):
    document_id: str = Field(max_length=160)
    document_number: str | None = Field(default=None, max_length=160)
    locator: str | None = Field(default=None, max_length=200)


class HistoryMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1, max_length=3000)
    as_of: date | None = None
    citations: list[HistoryCitation] = Field(default_factory=list, max_length=8)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=32, max_length=40)
    message: str = Field(min_length=1, max_length=4000)
    project: Literal['ring4'] | None = None
    as_of: date | None = None
    mode: Literal["agentic", "simple_rag", "agentic_rag"] = "agentic"
    request_id: UUID = Field(default_factory=uuid4)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=8)
    interaction: Interaction | None = None

    @model_validator(mode='after')
    def bounded_history(self):
        if sum(len(item.content) for item in self.history) > 12000:
            raise ValueError('History exceeds 12000 characters')
        for index, item in enumerate(self.history):
            if item.role != ('user' if index % 2 == 0 else 'assistant'):
                raise ValueError('History must alternate user and assistant messages')
        if len(self.history) % 2:
            raise ValueError('History must end with an assistant message')
        return self


class Claim(BaseModel):
    kind: Literal['legal_rule','applicability','context','procedure','contact'] = Field(default='legal_rule',
        description='applicability: dates, commencement, expiry or replacement only; legal_rule: rights, duties or conditions; context: project news only.')
    text: str = Field(min_length=1, max_length=3000)
    citation_ids: list[str] = Field(min_length=1, max_length=8)
    section: Literal['direct', 'explanation', 'actions'] = 'direct'


class Draft(BaseModel):
    status: Literal["answered", "clarification_needed", "insufficient_evidence"]
    summary: str = Field(default='', max_length=2000, description='Internal introduction; never displayed as an answer.')
    claims: list[Claim] = Field(default_factory=list, max_length=10,
        description='The ONLY factual answer text displayed to the user. Must contain at least one sourced claim when status is answered; attach allowed citation IDs to each claim.')
    missing_facts: list[str] = Field(default_factory=list, max_length=6)
    next_steps: list[str] = Field(default_factory=list, max_length=6)
    out_of_scope: bool = False


class ChatResult(BaseModel):
    status: Status
    publication_profile: str = 'staging'
    quality_status: str = 'academic_prototype'
    retrieval_mode: str = 'unavailable'
    coverage_gaps: list[dict] = Field(default_factory=list)
    content: str
    citations: list[Citation] = Field(default_factory=list)
    verified_claims: list[Claim] = Field(default_factory=list)
    answer_schema_version: Literal[1, 2] = 1
    answer_sections: list[AnswerSection] = Field(default_factory=list, max_length=3)
    answer_notices: list[str] = Field(default_factory=list, max_length=5,
        description='Fixed runtime limitations only; never model summary or procedural instructions.')
    clarification: Clarification | None = None
    source_context: dict = Field(default_factory=dict)
    need_more_context: Literal['stage', 'date', 'place', 'source', 'document_type', 'land_type'] | None = None
    as_of: date
    corpus_release: str | None = None
    trace_id: str
    trace: list[TraceEvent] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    llm_calls: int = 0
    embedding_calls: int = 0
    tool_calls: int = 0
    token_usage: int = 0
    elapsed_ms: int = 0
    model: str
    embedding_model: str
    mode: str
    support_level: Literal["full", "partial", "insufficient"] = "insufficient"
    retry_after: int | None = None
    retrieved_chunk_ids: list[str] = Field(default_factory=list)
    evidence_chunk_ids: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def valid_sections(self):
        if self.answer_schema_version == 2:
            indexes = [i for section in self.answer_sections for i in section.claim_indexes]
            if (len(indexes) != len(set(indexes)) or set(indexes) != set(range(len(self.verified_claims)))
                    or len({s.kind for s in self.answer_sections}) != len(self.answer_sections)):
                raise ValueError('Answer sections must reference each verified claim exactly once')
            if any(self.verified_claims[i].section!=section.kind for section in self.answer_sections for i in section.claim_indexes):
                raise ValueError('Answer section differs from the verified claim section')
            if self.status == 'answered' and not self.verified_claims:
                raise ValueError('An answered result needs verified claims')
            cited={citation.id for citation in self.citations}
            if len(cited)!=len(self.citations) or any(set(claim.citation_ids)-cited for claim in self.verified_claims):
                raise ValueError('Verified claim citations must exist uniquely in the result')
        return self
