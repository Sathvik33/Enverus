import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.repositories import TableChunkRepository
from app.embeddings.text_embeddings import embed_single
from app.schemas.retrieval import RetrievalResult


async def table_search(query: str, document_id: str, session: AsyncSession) -> list[RetrievalResult]:
    settings = get_settings()

    query_embedding = embed_single(query)

    if not query_embedding:
        return []

    repo = TableChunkRepository(session)

    results_from_db = await repo.search_by_vector(
        query_embedding,
        uuid.UUID(document_id),
        top_k=settings.TOP_K,
    )

    results = []

    for chunk, similarity in results_from_db:
        metadata = chunk.metadata_ or {}

        content = (
            metadata.get("text_representation")
            or chunk.table_content
        )

        results.append(
            RetrievalResult(
                id=str(chunk.id),
                content=content,
                score=float(similarity),
                page_number=chunk.page_number,
                section=chunk.section,
                source_type="table",
                metadata={
                    "table_data": chunk.table_data,
                    **metadata,
                },
            )
        )

    return results