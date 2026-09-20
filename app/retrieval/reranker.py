import re
from sentence_transformers import CrossEncoder

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.retrieval import FusedResult


logger = get_logger(__name__)

_reranker = None


def _get_reranker() -> CrossEncoder:
    global _reranker

    if _reranker is None:
        settings = get_settings()

        logger.info(
            "loading_reranker",
            model=settings.RERANKER_MODEL,
        )

        try:
            _reranker = CrossEncoder(settings.RERANKER_MODEL, local_files_only=True)
        except Exception:
            _reranker = CrossEncoder(settings.RERANKER_MODEL)

    return _reranker


def _candidate_text(candidate: FusedResult, query: str = "") -> str:
    parts = []
    content = candidate.content or ""

    # focus on referenced figure or table occurrence if queried
    if query:
        target_match = re.search(r'\b(?:figure|fig\.?|table)\s*(\d+)\b', query, re.I)
        if target_match:
            pattern = rf'\b(?:figure|fig\.?|table)\s*{target_match.group(1)}\b'
            m = re.search(pattern, content, re.I)
            if m:
                start = max(0, m.start() - 300)
                end = min(len(content), m.end() + 1500)
                content = content[start:end]

    if content:
        parts.append(content)

    if candidate.caption:
        parts.append(f"Caption: {candidate.caption}")

    if candidate.section:
        parts.append(f"Section: {candidate.section}")

    if candidate.page_number is not None:
        parts.append(f"Page: {candidate.page_number}")

    return "\n".join(parts)


def rerank(query: str, candidates: list[FusedResult], top_k: int | None = None) -> list[FusedResult]:
    if not candidates:
        return []

    settings = get_settings()

    if top_k is None:
        top_k = settings.FINAL_TOP_K

    reranker = _get_reranker()

    pairs = [
        (query, _candidate_text(candidate, query))
        for candidate in candidates
    ]

    scores = reranker.predict(
        pairs,
        show_progress_bar=False,
    )

    ranked = []

    for candidate, score in zip(candidates, scores):
        candidate.metadata = {
            **(candidate.metadata or {}),
            "reranker_score": float(score),
        }

        ranked.append((candidate, float(score)))

    ranked.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    return [
        candidate
        for candidate, _ in ranked[:top_k]
    ]