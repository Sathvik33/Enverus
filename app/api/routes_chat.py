import json
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.graph.workflow import answer_query, prepare_stream_context
from app.llm.provider import stream_response
from app.guardrails.output_guardrail import validate_output
from app.db.database import get_session_factory
from app.db.repositories import ChatHistoryRepository
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if not request.document_id.strip():
        raise HTTPException(status_code=400, detail="Document ID required")

    async def event_generator():
        try:
            stream_ctx = await prepare_stream_context(request.document_id, request.query)

            metadata = {
                "type": "metadata",
                "citations": stream_ctx["citations"],
                "evidence": stream_ctx["evidence"],
                "retrieval_trace": stream_ctx["retrieval_trace"],
            }
            yield f"data: {json.dumps(metadata)}\n\n"

            fallback = stream_ctx.get("fallback_answer")
            full_text = ""
            if fallback:
                yield f"data: {json.dumps({'type': 'token', 'token': fallback})}\n\n"
                full_text = fallback
            else:
                sys_prompt = stream_ctx["system_prompt"]
                prompt = stream_ctx["prompt"]
                async for token in stream_response(sys_prompt, prompt):
                    full_text += token
                    yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

            is_valid, cleaned_answer, _ = validate_output(
                full_text, stream_ctx.get("evidence_raw", []), request.query
            )

            if request.user_id:
                try:
                    user_uuid = uuid.UUID(request.user_id)
                    doc_uuid = uuid.UUID(request.document_id)
                    factory = get_session_factory()
                    async with factory() as session:
                        repo = ChatHistoryRepository(session)
                        await repo.create(
                            user_id=user_uuid,
                            document_id=doc_uuid,
                            query=request.query,
                            answer=cleaned_answer,
                            citations=stream_ctx["citations"],
                            evidence=stream_ctx["evidence"],
                        )
                except Exception as hist_err:
                    logger.warning("history_save_failed", error=str(hist_err))

            done_payload = {
                "type": "done",
                "final_answer": cleaned_answer,
                "citations": stream_ctx["citations"],
                "evidence": stream_ctx["evidence"],
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception as e:
            logger.error("chat_stream_failed", error=str(e), document_id=request.document_id)
            err_payload = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(err_payload)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if not request.document_id.strip():
        raise HTTPException(status_code=400, detail="Document ID required")

    try:
        result = await answer_query(request.document_id, request.query)

        if request.user_id:
            try:
                user_uuid = uuid.UUID(request.user_id)
                doc_uuid = uuid.UUID(request.document_id)
                factory = get_session_factory()
                async with factory() as session:
                    repo = ChatHistoryRepository(session)
                    citations_data = [
                        c.model_dump() if hasattr(c, "model_dump") else c
                        for c in result.get("citations", [])
                    ]
                    evidence_data = [
                        e.model_dump() if hasattr(e, "model_dump") else e
                        for e in result.get("evidence", [])
                    ]
                    await repo.create(
                        user_id=user_uuid,
                        document_id=doc_uuid,
                        query=request.query,
                        answer=result.get("answer", ""),
                        citations=citations_data,
                        evidence=evidence_data,
                    )
            except Exception as hist_err:
                logger.warning("history_save_failed", error=str(hist_err))

        return result
    except Exception as e:
        logger.error("chat_failed", error=str(e), document_id=request.document_id)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")
