from langgraph.graph import StateGraph, START, END
from app.graph.state import RAGState
from app.graph.nodes import (
    input_guardrail_node,
    query_analyzer_node,
    retrieve_text_node,
    retrieve_bm25_node,
    retrieve_tables_node,
    retrieve_images_node,
    rrf_fusion_node,
    reranker_node,
    evidence_validator_node,
    context_builder_node,
    llm_answer_node,
    output_guardrail_node,
    query_rewriter_node,
    should_retry,
    build_llm_prompt,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_rag_graph():
    builder = StateGraph(RAGState)

    builder.add_node("input_guardrail", input_guardrail_node)
    builder.add_node("query_analyzer", query_analyzer_node)
    builder.add_node("retrieve_text", retrieve_text_node)
    builder.add_node("retrieve_bm25", retrieve_bm25_node)
    builder.add_node("retrieve_tables", retrieve_tables_node)
    builder.add_node("retrieve_images", retrieve_images_node)
    builder.add_node("rrf_fusion", rrf_fusion_node)
    builder.add_node("reranker", reranker_node)
    builder.add_node("evidence_validator", evidence_validator_node)
    builder.add_node("context_builder", context_builder_node)
    builder.add_node("llm_answer", llm_answer_node)
    builder.add_node("output_guardrail", output_guardrail_node)
    builder.add_node("query_rewriter", query_rewriter_node)

    builder.add_edge(START, "input_guardrail")
    builder.add_edge("input_guardrail", "query_analyzer")
    builder.add_edge("query_analyzer", "retrieve_text")
    builder.add_edge("retrieve_text", "retrieve_bm25")
    builder.add_edge("retrieve_bm25", "retrieve_tables")
    builder.add_edge("retrieve_tables", "retrieve_images")
    builder.add_edge("retrieve_images", "rrf_fusion")
    builder.add_edge("rrf_fusion", "reranker")
    builder.add_edge("reranker", "evidence_validator")

    builder.add_conditional_edges("evidence_validator", should_retry, {
        "context_builder": "context_builder",
        "query_rewriter": "query_rewriter",
    })

    builder.add_edge("query_rewriter", "retrieve_text")
    builder.add_edge("context_builder", "llm_answer")
    builder.add_edge("llm_answer", "output_guardrail")
    builder.add_edge("output_guardrail", END)

    graph = builder.compile()
    logger.info("rag_graph_compiled")
    return graph


def build_retrieval_graph():
    builder = StateGraph(RAGState)

    builder.add_node("input_guardrail", input_guardrail_node)
    builder.add_node("query_analyzer", query_analyzer_node)
    builder.add_node("retrieve_text", retrieve_text_node)
    builder.add_node("retrieve_bm25", retrieve_bm25_node)
    builder.add_node("retrieve_tables", retrieve_tables_node)
    builder.add_node("retrieve_images", retrieve_images_node)
    builder.add_node("rrf_fusion", rrf_fusion_node)
    builder.add_node("reranker", reranker_node)
    builder.add_node("evidence_validator", evidence_validator_node)
    builder.add_node("context_builder", context_builder_node)
    builder.add_node("query_rewriter", query_rewriter_node)

    builder.add_edge(START, "input_guardrail")
    builder.add_edge("input_guardrail", "query_analyzer")
    builder.add_edge("query_analyzer", "retrieve_text")
    builder.add_edge("retrieve_text", "retrieve_bm25")
    builder.add_edge("retrieve_bm25", "retrieve_tables")
    builder.add_edge("retrieve_tables", "retrieve_images")
    builder.add_edge("retrieve_images", "rrf_fusion")
    builder.add_edge("rrf_fusion", "reranker")
    builder.add_edge("reranker", "evidence_validator")

    builder.add_conditional_edges("evidence_validator", should_retry, {
        "context_builder": "context_builder",
        "query_rewriter": "query_rewriter",
    })

    builder.add_edge("query_rewriter", "retrieve_text")
    builder.add_edge("context_builder", END)

    graph = builder.compile()
    logger.info("retrieval_graph_compiled")
    return graph


_graph = None
_retrieval_graph = None


def get_rag_graph():
    global _graph
    if _graph is None:
        _graph = build_rag_graph()
    return _graph


def get_retrieval_graph():
    global _retrieval_graph
    if _retrieval_graph is None:
        _retrieval_graph = build_retrieval_graph()
    return _retrieval_graph


async def prepare_stream_context(document_id: str, query: str) -> dict:
    graph = get_retrieval_graph()
    initial_state = {
        "query": query,
        "document_id": document_id,
        "retry_count": 0,
    }

    result = await graph.ainvoke(initial_state)

    from app.schemas.chat import Citation, Evidence
    citations = [Citation(**c).model_dump() for c in result.get("citations", [])]
    evidence = [Evidence(**{
        "id": e.get("id", ""),
        "content": e.get("content", ""),
        "score": e.get("rrf_score", e.get("score", 0)),
        "page_number": e.get("page_number", 0),
        "section": e.get("section", ""),
        "source_type": e.get("source_type", "text"),
        "image_path": e.get("image_path"),
        "caption": e.get("caption"),
    }).model_dump() for e in result.get("evidence", [])]

    trace = {
        "query": query,
        "query_analysis": {
            "query_type": result.get("query_type", ""),
            "needs_text": result.get("needs_text", True),
            "needs_table": result.get("needs_table", False),
            "needs_image": result.get("needs_image", False),
        },
        "text_results": result.get("text_results", []),
        "bm25_results": result.get("bm25_results", []),
        "table_results": result.get("table_results", []),
        "image_results": result.get("image_results", []),
        "rrf_results": result.get("fused_results", []),
        "reranked_results": result.get("reranked_results", []),
        "final_evidence": result.get("evidence", []),
    }

    sys_prompt, prompt, fallback = build_llm_prompt(result)

    return {
        "citations": citations,
        "evidence": evidence,
        "retrieval_trace": trace,
        "system_prompt": sys_prompt,
        "prompt": prompt,
        "fallback_answer": fallback,
        "evidence_raw": result.get("evidence", []),
    }


async def answer_query(document_id: str, query: str) -> dict:
    graph = get_rag_graph()
    initial_state = {
        "query": query,
        "document_id": document_id,
        "retry_count": 0,
    }

    result = await graph.ainvoke(initial_state)

    from app.schemas.chat import ChatResponse, Citation, Evidence, RetrievalTrace
    citations = [Citation(**c) for c in result.get("citations", [])]
    evidence = [Evidence(**{
        "id": e.get("id", ""),
        "content": e.get("content", ""),
        "score": e.get("rrf_score", e.get("score", 0)),
        "page_number": e.get("page_number", 0),
        "section": e.get("section", ""),
        "source_type": e.get("source_type", "text"),
        "image_path": e.get("image_path"),
        "caption": e.get("caption"),
    }) for e in result.get("evidence", [])]

    trace_data = result.get("retrieval_trace", {})
    trace = RetrievalTrace(**trace_data) if trace_data else None

    return ChatResponse(
        answer=result.get("answer", "No answer generated"),
        citations=citations,
        evidence=evidence,
        retrieval_trace=trace,
    ).model_dump()
