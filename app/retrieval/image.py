import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.repositories import ImageChunkRepository
from app.embeddings.image_embeddings import embed_text_for_image_search
from app.schemas.retrieval import RetrievalResult


async def image_search(query: str, document_id: str, session: AsyncSession) -> list[RetrievalResult]:
    settings = get_settings()

    query_embedding = embed_text_for_image_search(query)

    if not query_embedding:
        return []

    repo = ImageChunkRepository(session)

    results_from_db = await repo.search_by_vector(
        query_embedding,
        uuid.UUID(document_id),
        top_k=settings.TOP_K,
    )

    results = []

    for chunk, similarity in results_from_db:
        metadata = chunk.metadata_ or {}

        content = (
            chunk.caption
            or metadata.get("text_representation")
            or f"Image on page {chunk.page_number}"
        )

        results.append(
            RetrievalResult(
                id=str(chunk.id),
                content=content,
                score=float(similarity),
                page_number=chunk.page_number,
                section=chunk.section,
                source_type="image",
                image_path=chunk.image_path,
                caption=chunk.caption,
                metadata=metadata,
            )
        )

    return results