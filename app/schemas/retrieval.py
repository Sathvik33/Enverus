from pydantic import BaseModel, Field
from typing import Optional


class RetrievalResult(BaseModel):
    id: str
    content: str = ""
    score: float = 0.0
    page_number: int = 0
    section: str = ""
    source_type: str = "text"
    image_path: Optional[str] = None
    caption: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class QueryAnalysis(BaseModel):
    query_type: str = "factual_text"
    needs_text: bool = True
    needs_table: bool = False
    needs_image: bool = False
    rewritten_query: str = ""
    search_terms: list[str] = Field(default_factory=list)


class FusedResult(BaseModel):
    id: str
    content: str = ""
    rrf_score: float = 0.0
    page_number: int = 0
    section: str = ""
    source_type: str = "text"
    sources: list[str] = Field(default_factory=list)
    image_path: Optional[str] = None
    caption: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
