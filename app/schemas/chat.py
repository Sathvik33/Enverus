from pydantic import BaseModel, Field
from typing import Optional


class Citation(BaseModel):
    page_number: int
    section: str = ""
    source_type: str = "text"
    source_id: str = ""
    content_preview: str = ""


class Evidence(BaseModel):
    id: str
    content: str
    score: float
    page_number: int
    section: str = ""
    source_type: str = "text"
    image_path: Optional[str] = None
    caption: Optional[str] = None


class RetrievalTrace(BaseModel):
    query: str
    query_analysis: dict = Field(default_factory=dict)
    text_results: list[dict] = Field(default_factory=list)
    bm25_results: list[dict] = Field(default_factory=list)
    table_results: list[dict] = Field(default_factory=list)
    image_results: list[dict] = Field(default_factory=list)
    rrf_results: list[dict] = Field(default_factory=list)
    reranked_results: list[dict] = Field(default_factory=list)
    final_evidence: list[dict] = Field(default_factory=list)


class ChatRequest(BaseModel):
    document_id: str
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    retrieval_trace: Optional[RetrievalTrace] = None
    session_id: Optional[str] = None


class ChatSessionCreate(BaseModel):
    document_id: str
    user_id: Optional[str] = None
    title: Optional[str] = "New Chat"


class ChatMessageItem(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: list[dict] = []
    evidence: list[dict] = []
    created_at: str


class ChatSessionItem(BaseModel):
    id: str
    user_id: str
    document_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ChatSessionDetail(BaseModel):
    id: str
    user_id: str
    document_id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessageItem] = []
