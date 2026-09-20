import pytest
import uuid
from app.schemas.chat import (
    ChatSessionCreate,
    ChatMessageItem,
    ChatSessionItem,
    ChatSessionDetail,
    ChatRequest,
)
from app.graph.nodes import build_llm_prompt
from app.graph.state import RAGState


def test_session_schemas():
    uid = str(uuid.uuid4())
    did = str(uuid.uuid4())
    sid = str(uuid.uuid4())
    create_req = ChatSessionCreate(document_id=did, user_id=uid, title="Analysis Chat")
    assert create_req.title == "Analysis Chat"
    assert create_req.document_id == did

    msg = ChatMessageItem(
        id=str(uuid.uuid4()),
        session_id=sid,
        role="user",
        content="What frameworks were tested?",
        citations=[],
        evidence=[],
        created_at="2026-09-20T12:00:00Z",
    )
    assert msg.role == "user"
    assert msg.content == "What frameworks were tested?"

    detail = ChatSessionDetail(
        id=sid,
        user_id=uid,
        document_id=did,
        title="Analysis Chat",
        created_at="2026-09-20T12:00:00Z",
        updated_at="2026-09-20T12:05:00Z",
        messages=[msg],
    )
    assert len(detail.messages) == 1
    assert detail.title == "Analysis Chat"

    session_item = ChatSessionItem(
        id=sid,
        user_id=uid,
        document_id=did,
        title="Analysis Chat",
        created_at="2026-09-20T12:00:00Z",
        updated_at="2026-09-20T12:05:00Z",
        message_count=1,
    )
    assert session_item.message_count == 1


def test_chat_request_session_id():
    req = ChatRequest(
        document_id="doc-123",
        query="Follow up question",
        session_id="sess-456",
        user_id="user-789",
    )
    assert req.session_id == "sess-456"
    assert req.user_id == "user-789"


def test_clean_session_prompt_isolation():
    """A fresh session (or new chat) with empty conversation_history must NOT have previous dialogue."""
    state_clean: RAGState = {
        "query": "What is DevAI?",
        "document_id": "test-123",
        "evidence": [{"page_number": 1, "section": "Intro", "content": "DevAI is a benchmark."}],
        "conversation_history": [],
    }
    _, prompt_clean, fallback = build_llm_prompt(state_clean)
    assert fallback == ""
    assert "PREVIOUS CONVERSATION IN THIS CHAT:" not in prompt_clean
    assert "What is DevAI?" in prompt_clean


def test_multi_turn_session_prompt_injection():
    """Follow-up questions in the same session retain conversation history in the prompt context."""
    history = [
        {"role": "user", "content": "What frameworks were benchmarked?"},
        {"role": "assistant", "content": "MetaGPT, GPT-Pilot, and OpenHands."},
    ]
    state_with_history: RAGState = {
        "query": "Which of them performed best?",
        "document_id": "test-123",
        "evidence": [{"page_number": 2, "section": "Results", "content": "MetaGPT scored highest."}],
        "conversation_history": history,
    }
    _, prompt_with_history, fallback = build_llm_prompt(state_with_history)
    assert fallback == ""
    assert "PREVIOUS CONVERSATION IN THIS CHAT:" in prompt_with_history
    assert "User: What frameworks were benchmarked?" in prompt_with_history
    assert "Assistant: MetaGPT, GPT-Pilot, and OpenHands." in prompt_with_history
    assert "Which of them performed best?" in prompt_with_history


def test_session_history_window_limit():
    """Ensure older dialogue is capped to the most recent 4 turns to avoid exceeding context."""
    history = [
        {"role": "user", "content": f"Turn {i} question"}
        if i % 2 == 0
        else {"role": "assistant", "content": f"Turn {i} answer"}
        for i in range(10)
    ]
    state_large: RAGState = {
        "query": "Final question?",
        "document_id": "test-123",
        "evidence": [{"page_number": 3, "section": "Summary", "content": "Summary info."}],
        "conversation_history": history,
    }
    _, prompt, _ = build_llm_prompt(state_large)
    # The first few turns should not be in the prompt window (only the last 4: turns 6, 7, 8, 9)
    assert "Turn 0 question" not in prompt
    assert "Turn 1 answer" not in prompt
    assert "Turn 8 question" in prompt
    assert "Turn 9 answer" in prompt
