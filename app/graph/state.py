from typing import TypedDict, Optional, Annotated
from operator import add


class RAGState(TypedDict, total=False):
    query: str
    document_id: str
    cleaned_query: str
    pii_findings: list[dict]

    query_type: str
    needs_text: bool
    needs_table: bool
    needs_image: bool
    rewritten_query: str
    search_terms: list[str]

    text_results: list[dict]
    bm25_results: list[dict]
    table_results: list[dict]
    image_results: list[dict]

    fused_results: list[dict]
    reranked_results: list[dict]

    evidence_sufficient: bool
    evidence_reason: str
    evidence: list[dict]

    text_context: list[dict]
    table_context: list[dict]
    image_context: list[dict]
    citations: list[dict]

    answer: str
    output_valid: bool
    output_reason: str

    retry_count: int
    retrieval_trace: dict
