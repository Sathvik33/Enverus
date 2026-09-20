import json
import re
import uuid
from app.graph.state import RAGState
from app.guardrails.input_guardrail import validate_input
from app.guardrails.output_guardrail import validate_output
from app.retrieval.dense import dense_text_search
from app.retrieval.bm25 import bm25_search
from app.retrieval.table import table_search
from app.retrieval.image import image_search
from app.retrieval.rrf import reciprocal_rank_fusion
from app.retrieval.reranker import rerank
from app.llm.provider import generate_response
from app.llm.prompts import SYSTEM_PROMPT, QUERY_ANALYSIS_PROMPT, ANSWER_PROMPT, EVIDENCE_VALIDATION_PROMPT
from app.db.database import get_session_factory
from app.db.repositories import TextChunkRepository
from app.schemas.retrieval import RetrievalResult
from app.core.logging import get_logger

logger = get_logger(__name__)


def _to_dicts(results) -> list[dict]:
    return [r.model_dump() for r in results]


async def input_guardrail_node(state: RAGState) -> dict:
    query = state["query"]
    cleaned, pii = validate_input(query)
    return {"cleaned_query": cleaned, "pii_findings": pii}


async def query_analyzer_node(state: RAGState) -> dict:
    query = state.get("cleaned_query", state["query"])
    prompt = QUERY_ANALYSIS_PROMPT.format(query=query)
    try:
        response = await generate_response("You are a query analysis assistant. Respond only in JSON.", prompt)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        analysis = json.loads(response)
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("query_analysis_fallback", error=str(e))
        query_lower = query.lower()
        analysis = {
            "query_type": "mixed",
            "needs_text": True,
            "needs_table": any(w in query_lower for w in ["table", "cost", "rate", "number", "percentage", "score", "$", "average", "expensive"]),
            "needs_image": any(w in query_lower for w in ["figure", "fig", "image", "diagram", "show", "visual", "picture"]),
            "rewritten_query": query,
            "search_terms": query.split()[:5],
        }
        if not analysis["needs_table"] and not analysis["needs_image"]:
            analysis["query_type"] = "factual_text"

    query_lower = query.lower()
    overview_phrases = [
        "what is this paper about", "what is the paper about", "what is this document about",
        "what is the document about", "what is this about", "what is this research about",
        "summarize the paper", "summary of the paper", "summary of the document",
        "overview of the paper", "overview of the document", "main topic of the paper",
        "purpose of the paper", "explain the paper", "explain this paper",
    ]
    is_fig_or_table = bool(re.search(r'\b(?:figure|fig\.?|table)\s*\d+\b', query_lower))
    is_overview = (any(phrase in query_lower for phrase in overview_phrases) or query_lower.strip() in ("summary", "overview", "what is this about")) and not is_fig_or_table
    if is_overview:
        analysis["query_type"] = "overview"
        analysis["needs_text"] = True
        analysis["rewritten_query"] = f"{query} abstract introduction main contribution overview summary"
        analysis["search_terms"] = ["abstract", "introduction", "overview", "contributions", "paper summary"]

    return {
        "query_type": analysis.get("query_type", "mixed"),
        "needs_text": analysis.get("needs_text", True),
        "needs_table": analysis.get("needs_table", False),
        "needs_image": analysis.get("needs_image", False),
        "rewritten_query": analysis.get("rewritten_query", query),
        "search_terms": analysis.get("search_terms", []),
    }


async def retrieve_text_node(state: RAGState) -> dict:
    query = state.get("rewritten_query", state.get("cleaned_query", state["query"]))
    doc_id = state["document_id"]
    factory = get_session_factory()
    async with factory() as session:
        results = await dense_text_search(query, doc_id, session)

        # targeted search for explicitly queried figures or tables
        target_match = re.search(r'\b(figure|fig\.?|table)\s*(\d+)\b', query.lower())
        if target_match:
            kind = "Figure" if "fig" in target_match.group(1) else "Table"
            num = target_match.group(2)
            repo = TextChunkRepository(session)
            matched = await repo.search_by_pattern(uuid.UUID(doc_id), f"{kind} {num}", limit=5)
            existing_ids = {r.id for r in results}
            for c in matched:
                if str(c.id) not in existing_ids and re.search(rf'\b(?:figure|fig\.?|table)\s+{num}(?!\d)', c.content, re.I):
                    results.insert(0, RetrievalResult(
                        id=str(c.id),
                        content=c.content,
                        score=0.95,
                        page_number=c.page_number,
                        section=c.section,
                        source_type="text",
                        metadata=c.metadata_ or {},
                    ))
    return {"text_results": _to_dicts(results)}


async def retrieve_bm25_node(state: RAGState) -> dict:
    query = state.get("rewritten_query", state.get("cleaned_query", state["query"]))
    doc_id = state["document_id"]
    factory = get_session_factory()
    async with factory() as session:
        results = await bm25_search(query, doc_id, session)
    return {"bm25_results": _to_dicts(results)}


async def retrieve_tables_node(state: RAGState) -> dict:
    if not state.get("needs_table", True):
        return {"table_results": []}
    query = state.get("rewritten_query", state.get("cleaned_query", state["query"]))
    doc_id = state["document_id"]
    factory = get_session_factory()
    async with factory() as session:
        results = await table_search(query, doc_id, session)
    return {"table_results": _to_dicts(results)}


async def retrieve_images_node(state: RAGState) -> dict:
    if not state.get("needs_image", False):
        return {"image_results": []}
    query = state.get("rewritten_query", state.get("cleaned_query", state["query"]))
    doc_id = state["document_id"]
    factory = get_session_factory()
    async with factory() as session:
        results = await image_search(query, doc_id, session)
    return {"image_results": _to_dicts(results)}


async def rrf_fusion_node(state: RAGState) -> dict:
    from app.schemas.retrieval import RetrievalResult

    all_lists = []
    for key in ["text_results", "bm25_results", "table_results", "image_results"]:
        items = state.get(key, [])
        if items:
            all_lists.append([RetrievalResult(**r) for r in items])

    if not all_lists:
        return {"fused_results": []}

    fused = reciprocal_rank_fusion(*all_lists)
    return {"fused_results": [f.model_dump() for f in fused]}


async def reranker_node(state: RAGState) -> dict:
    from app.schemas.retrieval import FusedResult

    fused = state.get("fused_results", [])
    if not fused:
        return {"reranked_results": []}

    query = state.get("rewritten_query", state.get("cleaned_query", state["query"]))
    candidates = [FusedResult(**f) for f in fused[:15]]
    reranked = rerank(query, candidates)
    return {"reranked_results": [r.model_dump() for r in reranked]}


def _extract_evidence_snippet(content: str, query: str = "", max_chars: int = 1500) -> str:
    if not content or len(content) <= max_chars:
        return content
    if query:
        target_match = re.search(r'\b(?:figure|fig\.?|table)\s*(\d+)\b', query, re.I)
        if target_match:
            pattern = rf'\b(?:figure|fig\.?|table)\s*{target_match.group(1)}\b'
            m = re.search(pattern, content, re.I)
            if m:
                start = max(0, m.start() - 300)
                end = min(len(content), m.end() + 1200)
                return content[start:end]
    half = max_chars // 2
    return content[:half] + "\n...\n" + content[-half:]


async def evidence_validator_node(state: RAGState) -> dict:
    reranked = state.get("reranked_results", [])
    if not reranked:
        return {"evidence_sufficient": False, "evidence_reason": "No results found", "evidence": []}

    query = state.get("cleaned_query", state["query"])
    evidence_text = "\n".join(
        f"[Page {r.get('page_number')}, {r.get('section', '')}]: {_extract_evidence_snippet(r.get('content', ''), query, 1200)}"
        for r in reranked[:5]
    )

    if state.get("query_type") in ("overview", "summary") and reranked:
        return {
            "evidence_sufficient": True,
            "evidence_reason": "Document overview evidence available",
            "evidence": reranked[:5],
        }

    try:
        prompt = EVIDENCE_VALIDATION_PROMPT.format(query=query, evidence=evidence_text)
        response = await generate_response("Respond only in JSON.", prompt)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        validation = json.loads(response)
        sufficient = validation.get("sufficient", True)
        reason = validation.get("reason", "")
    except Exception:
        sufficient = len(reranked) >= 1
        reason = "Fallback: evidence available" if sufficient else "No evidence"

    return {
        "evidence_sufficient": sufficient,
        "evidence_reason": reason,
        "evidence": reranked[:5],
    }


def _clean_section(raw_section: str) -> str:
    if not raw_section:
        return ""
    part = raw_section.split(" > ")[-1].strip()
    return re.sub(r"[*_~#]+", "", part).strip()


def _format_source_label(e: dict) -> str:
    page = e.get("page_number", "?")
    sec = _clean_section(e.get("section", ""))
    st = e.get("source_type", "text")

    label_parts = [f"Page {page}"]
    if sec:
        label_parts.append(sec if sec.lower().startswith("section") else f"Section {sec}")
    if "table" in st:
        label_parts.append("Table")
    elif "image" in st:
        label_parts.append("Figure")

    return f"[{', '.join(label_parts)}]"


async def context_builder_node(state: RAGState) -> dict:
    evidence = state.get("evidence", [])
    text_ctx = [e for e in evidence if e.get("source_type") in ("text", "text_bm25")]
    table_ctx = [e for e in evidence if e.get("source_type") == "table"]
    image_ctx = [e for e in evidence if e.get("source_type") == "image"]

    citations = []
    for e in evidence:
        citations.append({
            "page_number": e.get("page_number", 0),
            "section": _clean_section(e.get("section", "")),
            "source_type": e.get("source_type", "text"),
            "source_id": e.get("id", ""),
            "content_preview": (e.get("content", ""))[:100],
        })

    return {
        "text_context": text_ctx,
        "table_context": table_ctx,
        "image_context": image_ctx,
        "citations": citations,
    }


def build_llm_prompt(state: RAGState) -> tuple[str, str, str]:
    evidence = state.get("evidence", [])
    if not evidence:
        return "", "", "I could not find sufficient evidence in the document."

    query = state.get("cleaned_query", state["query"])
    context_parts = []
    for i, e in enumerate(evidence, 1):
        source = _format_source_label(e)
        content = _extract_evidence_snippet(e.get("content", ""), query, 2500).strip()
        context_parts.append(f"Evidence Item {i} {source}:\n{content}")

    context = "\n\n---\n\n".join(context_parts)
    prompt = ANSWER_PROMPT.format(context=context, query=query)
    return SYSTEM_PROMPT, prompt, ""


async def llm_answer_node(state: RAGState) -> dict:
    sys_prompt, prompt, fallback = build_llm_prompt(state)
    if fallback:
        return {"answer": fallback}

    try:
        answer = await generate_response(sys_prompt, prompt)
    except Exception as e:
        logger.error("llm_answer_failed", error=str(e))
        answer = "I could not generate an answer due to a system error."

    return {"answer": answer}


async def output_guardrail_node(state: RAGState) -> dict:
    answer = state.get("answer", "")
    evidence = state.get("evidence", [])
    query = state.get("cleaned_query", state["query"])

    is_valid, cleaned, reason = validate_output(answer, evidence, query)

    trace = {
        "query": state.get("query", ""),
        "query_analysis": {
            "query_type": state.get("query_type", ""),
            "needs_text": state.get("needs_text", True),
            "needs_table": state.get("needs_table", False),
            "needs_image": state.get("needs_image", False),
        },
        "text_results": state.get("text_results", []),
        "bm25_results": state.get("bm25_results", []),
        "table_results": state.get("table_results", []),
        "image_results": state.get("image_results", []),
        "rrf_results": state.get("fused_results", []),
        "reranked_results": state.get("reranked_results", []),
        "final_evidence": state.get("evidence", []),
    }

    return {
        "answer": cleaned,
        "output_valid": is_valid,
        "output_reason": reason,
        "retrieval_trace": trace,
    }


def should_retry(state: RAGState) -> str:
    if state.get("evidence_sufficient", False):
        return "context_builder"
    retry = state.get("retry_count", 0)
    if retry >= 1:
        return "context_builder"
    return "query_rewriter"


async def query_rewriter_node(state: RAGState) -> dict:
    query = state.get("cleaned_query", state["query"])
    reason = state.get("evidence_reason", "")
    rewritten = f"{query} (looking for: {reason})"
    retry = state.get("retry_count", 0)
    return {
        "rewritten_query": rewritten,
        "retry_count": retry + 1,
    }
