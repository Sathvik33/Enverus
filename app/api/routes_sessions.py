import uuid
from fastapi import APIRouter, HTTPException, Query
from app.db.database import get_session_factory
from app.db.repositories import ChatSessionRepository
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionItem,
    ChatMessageItem,
    ChatSessionDetail,
)
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[ChatSessionItem])
async def list_sessions(user_id: str = Query(..., description="User UUID")):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    factory = get_session_factory()
    async with factory() as session:
        repo = ChatSessionRepository(session)
        sessions = await repo.get_user_sessions(user_uuid)
        
        items = []
        for s in sessions:
            msgs = await repo.get_session_messages(s.id)
            items.append(
                ChatSessionItem(
                    id=str(s.id),
                    user_id=str(s.user_id),
                    document_id=str(s.document_id),
                    title=s.title or "New Chat",
                    created_at=s.created_at.isoformat() if s.created_at else "",
                    updated_at=s.updated_at.isoformat() if s.updated_at else "",
                    message_count=len(msgs),
                )
            )
        return items


@router.post("", response_model=ChatSessionItem)
async def create_session(req: ChatSessionCreate):
    if not req.document_id:
        raise HTTPException(status_code=400, detail="Document ID required")
    if not req.user_id:
        raise HTTPException(status_code=400, detail="User ID required")

    try:
        user_uuid = uuid.UUID(req.user_id)
        doc_uuid = uuid.UUID(req.document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    factory = get_session_factory()
    async with factory() as session:
        repo = ChatSessionRepository(session)
        s = await repo.create_session(
            user_id=user_uuid,
            document_id=doc_uuid,
            title=req.title or "New Chat",
        )
        return ChatSessionItem(
            id=str(s.id),
            user_id=str(s.user_id),
            document_id=str(s.document_id),
            title=s.title,
            created_at=s.created_at.isoformat() if s.created_at else "",
            updated_at=s.updated_at.isoformat() if s.updated_at else "",
            message_count=0,
        )


@router.get("/{session_id}", response_model=ChatSessionDetail)
async def get_session_detail(session_id: str):
    try:
        s_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    factory = get_session_factory()
    async with factory() as session:
        repo = ChatSessionRepository(session)
        s = await repo.get_session(s_uuid)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")

        msgs = await repo.get_session_messages(s_uuid)
        message_items = [
            ChatMessageItem(
                id=str(m.id),
                session_id=str(m.session_id),
                role=m.role,
                content=m.content,
                citations=m.citations or [],
                evidence=m.evidence or [],
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
            for m in msgs
        ]

        return ChatSessionDetail(
            id=str(s.id),
            user_id=str(s.user_id),
            document_id=str(s.document_id),
            title=s.title,
            created_at=s.created_at.isoformat() if s.created_at else "",
            updated_at=s.updated_at.isoformat() if s.updated_at else "",
            messages=message_items,
        )


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    try:
        s_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format")

    factory = get_session_factory()
    async with factory() as session:
        repo = ChatSessionRepository(session)
        deleted = await repo.delete_session(s_uuid)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "deleted", "session_id": session_id}


@router.delete("")
async def clear_all_sessions(user_id: str = Query(..., description="User UUID")):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    factory = get_session_factory()
    async with factory() as session:
        repo = ChatSessionRepository(session)
        await repo.clear_user_sessions(user_uuid)
        return {"status": "cleared"}
