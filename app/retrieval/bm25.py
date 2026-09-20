import re
import uuid

from rank_bm25 import BM25Okapi
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.repositories import TextChunkRepository
from app.schemas.retrieval import RetrievalResult


def _tokenize(text: str) -> list[str]:
    """Tokenize text for BM25 retrieval."""

    if not text:
        return []

    return re.findall(r"\b[\w+#.-]+\b", text.lower())


async def bm25_search(query: str, document_id: str, session: AsyncSession) -> list[RetrievalResult]:
    settings = get_settings()

    repo = TextChunkRepository(session)
    chunks = await repo.get_all_for_document(uuid.UUID(document_id))

    if not chunks:
        return []

    query_tokens = _tokenize(query)

    if not query_tokens:
        return []

    corpus = [_tokenize(chunk.content) for chunk in chunks]

    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(query_tokens)

    scored = list(zip(chunks, scores))
    scored.sort(key=lambda item: item[1], reverse=True)

    results = []

    for chunk, score in scored[:settings.TOP_K]:
        score = float(score)

        if score <= 0:
            continue

        results.append(
            RetrievalResult(
                id=str(chunk.id),
                content=chunk.content,
                score=score,
                page_number=chunk.page_number,
                section=chunk.section,
                source_type="text_bm25",
                metadata=chunk.metadata_ or {},
            )
        )

    return results