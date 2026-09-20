import uuid
from fastapi import APIRouter, HTTPException, Query
from app.db.database import get_session_factory
from app.db.repositories import ChatHistoryRepository
from app.schemas.history import HistoryListResponse, ChatHistoryItem
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
async def get_history(user_id: str = Query(..., description="User UUID")):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    factory = get_session_factory()
    async with factory() as session:
        repo = ChatHistoryRepository(session)
        records = await repo.get_by_user(user_uuid)

        items = [
            ChatHistoryItem(
                id=str(r.id),
                user_id=str(r.user_id),
                document_id=str(r.document_id),
                query=r.query,
                answer=r.answer,
                citations=r.citations or [],
                evidence=r.evidence or [],
                created_at=r.created_at.isoformat(),
            )
            for r in records
        ]
        return HistoryListResponse(items=items)


@router.get("/{history_id}", response_model=ChatHistoryItem)
async def get_history_detail(history_id: str):
    try:
        hist_uuid = uuid.UUID(history_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid history ID format")

    factory = get_session_factory()
    async with factory() as session:
        repo = ChatHistoryRepository(session)
        r = await repo.get_by_id(hist_uuid)
        if not r:
            raise HTTPException(status_code=404, detail="History record not found")

        return ChatHistoryItem(
            id=str(r.id),
            user_id=str(r.user_id),
            document_id=str(r.document_id),
            query=r.query,
            answer=r.answer,
            citations=r.citations or [],
            evidence=r.evidence or [],
            created_at=r.created_at.isoformat(),
        )


@router.delete("")
async def clear_history(user_id: str = Query(..., description="User UUID")):
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")

    factory = get_session_factory()
    async with factory() as session:
        repo = ChatHistoryRepository(session)
        await repo.clear_for_user(user_uuid)
        return {"status": "cleared"}
