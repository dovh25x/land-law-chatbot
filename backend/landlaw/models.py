from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

ProjectID = Literal["ring4", "songhong", "olympic"]
Status = Literal["answered", "clarification_needed", "insufficient_evidence", "limited", "error"]


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


class Document(BaseModel):
    id: str
    title: str
    url: HttpUrl
    publication_url: HttpUrl | None = None
    source_kind: Literal["legal", "project_decision", "official_news"]
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
    source_files: list[SourceFile] = Field(default_factory=list)
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
    page: int | None = None
    source_url: str | None = None


class TraceEvent(BaseModel):
    step: str
    tool: str | None = None
    summary: str
    document_ids: list[str] = Field(default_factory=list)
    elapsed_ms: int = 0


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=32, max_length=40)
    message: str = Field(min_length=1, max_length=4000)
    project: ProjectID | None = None
    as_of: date | None = None
    mode: Literal["agentic"] = "agentic"


class Claim(BaseModel):
    kind: Literal['legal_rule','applicability','context'] = Field(default='legal_rule',
        description='applicability: dates, commencement, expiry or replacement only; legal_rule: rights, duties or conditions; context: project news only.')
    text: str = Field(min_length=1, max_length=3000)
    citation_ids: list[str] = Field(min_length=1, max_length=8)


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
