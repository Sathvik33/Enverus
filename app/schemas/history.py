from pydantic import BaseModel
from typing import Any


class ChatHistoryItem(BaseModel):
    id: str
    user_id: str
    document_id: str
    query: str
    answer: str
    citations: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    created_at: str


class HistoryListResponse(BaseModel):
    items: list[ChatHistoryItem]
