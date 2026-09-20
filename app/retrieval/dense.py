import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.repositories import TextChunkRepository
from app.embeddings.text_embeddings import embed_single
from app.schemas.retrieval import RetrievalResult


async def dense_text_search(query: str, document_id: str, session: AsyncSession) -> list[RetrievalResult]:
    settings = get_settings()

    query_embedding = embed_single(query)

    if not query_embedding:
        return []

    repo = TextChunkRepository(session)

    results_from_db = await repo.search_by_vector(
        query_embedding,
        uuid.UUID(document_id),
        top_k=settings.TOP_K,
    )

    results = []
    seen_ids = set()

    for chunk, similarity in results_from_db:
        seen_ids.add(chunk.id)
        results.append(
            RetrievalResult(
                id=str(chunk.id),
                content=chunk.content,
                score=float(similarity),
                page_number=chunk.page_number,
                section=chunk.section,
                source_type="text_dense",
                metadata=chunk.metadata_ or {},
            )
        )

    query_lower = query.lower()
    is_overview = any(w in query_lower for w in ["about", "summar", "overview", "what is this", "main topic", "purpose", "explain the paper", "paper about"])
    if is_overview:
        initial = await repo.get_initial_chunks(uuid.UUID(document_id), limit=3)
        for init_chunk in initial:
            if init_chunk.id not in seen_ids:
                seen_ids.add(init_chunk.id)
                results.append(
                    RetrievalResult(
                        id=str(init_chunk.id),
                        content=init_chunk.content,
                        score=0.9,
                        page_number=init_chunk.page_number,
                        section=init_chunk.section,
                        source_type="text_dense",
                        metadata=init_chunk.metadata_ or {},
                    )
                )

    return results