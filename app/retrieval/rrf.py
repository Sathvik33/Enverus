from collections import defaultdict

from app.core.config import get_settings
from app.schemas.retrieval import FusedResult, RetrievalResult


def reciprocal_rank_fusion(*result_lists: list[RetrievalResult], k: int | None = None) -> list[FusedResult]:
    """Fuse multiple ranked retrieval lists using Reciprocal Rank Fusion."""

    if k is None:
        k = get_settings().RRF_K

    rrf_scores = defaultdict(float)
    items = {}
    source_ranks = defaultdict(dict)

    for list_index, result_list in enumerate(result_lists):
        if not result_list:
            continue

        source_name = result_list[0].source_type or f"retriever_{list_index}"

        for rank, result in enumerate(result_list, start=1):
            rrf_scores[result.id] += 1.0 / (k + rank)

            if result.id not in items:
                items[result.id] = result

            source_ranks[result.id][source_name] = rank

    sorted_ids = sorted(
        rrf_scores,
        key=rrf_scores.get,
        reverse=True,
    )

    fused = []

    for item_id in sorted_ids:
        item = items[item_id]

        fused.append(
            FusedResult(
                id=item_id,
                content=item.content,
                rrf_score=rrf_scores[item_id],
                page_number=item.page_number,
                section=item.section,
                source_type=item.source_type,
                sources=list(source_ranks[item_id].keys()),
                image_path=item.image_path,
                caption=item.caption,
                metadata={
                    **(item.metadata or {}),
                    "retrieval_ranks": source_ranks[item_id],
                },
            )
        )

    return fused