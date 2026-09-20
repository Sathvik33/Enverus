from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


_model = None


def _get_model() -> SentenceTransformer:
    global _model

    if _model is None:
        settings = get_settings()

        logger.info(
            "loading_text_embedding_model",
            model=settings.TEXT_EMBEDDING_MODEL,
        )

        _model = SentenceTransformer(
            settings.TEXT_EMBEDDING_MODEL
        )

    return _model


def embed_texts(
    texts: list[str],
) -> list[list[float]]:

    if not texts:
        return []

    model = _get_model()

    cleaned = [
        text.strip()
        for text in texts
        if text and text.strip()
    ]

    if not cleaned:
        return []

    embeddings = model.encode(
        cleaned,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return embeddings.tolist()


def embed_single(text: str,) -> list[float]:

    if not text or not text.strip():
        return []

    result = embed_texts([text])

    return result[0] if result else []