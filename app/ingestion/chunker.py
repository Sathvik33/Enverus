from app.schemas.document import (
    ParsedElement,
    ElementType,
    TextChunkSchema,
    TableChunkSchema,
)
from app.core.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)


def estimate_tokens(text: str) -> int:
    """
    Lightweight token estimate.

    This is intentionally a heuristic and should not be interpreted
    as the exact tokenizer count of the downstream LLM.
    """
    if not text:
        return 0

    return len(text.split())


def _take_last_tokens(
    parts: list[str],
    max_tokens: int,
) -> tuple[list[str], int]:

    if max_tokens <= 0:
        return [], 0

    combined = "\n\n".join(parts)
    tokens = combined.split()

    if len(tokens) <= max_tokens:
        return [combined], len(tokens)

    overlap_tokens = tokens[-max_tokens:]

    overlap_text = " ".join(overlap_tokens)

    return [overlap_text], len(overlap_tokens)


def chunk_elements(
    elements: list[ParsedElement],
    document_id: str,
) -> tuple[
    list[TextChunkSchema],
    list[TableChunkSchema],
]:

    settings = get_settings()

    chunk_size = settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP

    if chunk_size <= 0:
        raise ValueError("CHUNK_SIZE must be greater than zero")

    if overlap < 0:
        raise ValueError("CHUNK_OVERLAP cannot be negative")

    if overlap >= chunk_size:
        raise ValueError(
            "CHUNK_OVERLAP must be smaller than CHUNK_SIZE"
        )

    text_chunks: list[TextChunkSchema] = []
    table_chunks: list[TableChunkSchema] = []

    current_parts: list[str] = []
    current_tokens = 0
    current_page = 0
    current_section = ""
    current_parent = ""

    def flush_chunk() -> None:
        nonlocal current_parts
        nonlocal current_tokens
        nonlocal current_page
        nonlocal current_section
        nonlocal current_parent

        if not current_parts:
            return

        content = "\n\n".join(current_parts).strip()

        if not content:
            return

        text_chunks.append(
            TextChunkSchema(
                document_id=document_id,
                page_number=current_page,
                section=current_section,
                parent_section=current_parent,
                content=content,
                chunk_type="text",
                metadata={
                    "token_estimate": current_tokens,
                },
            )
        )

        # Keep an actual token-sized overlap instead of
        # blindly keeping the entire final paragraph.
        overlap_parts, overlap_tokens = _take_last_tokens(
            current_parts,
            overlap,
        )

        current_parts = overlap_parts
        current_tokens = overlap_tokens

    for elem in elements:

        # Tables are kept atomic and handled separately.
        if elem.element_type == ElementType.TABLE:
            table_chunks.append(
                TableChunkSchema(
                    document_id=document_id,
                    page_number=elem.page_number,
                    section=elem.section,
                    table_content=elem.content,
                    table_data=elem.metadata,
                    metadata={
                        "element_type": "table",
                        "bbox": elem.bbox,
                    },
                )
            )
            continue

        if elem.element_type not in (
            ElementType.TEXT,
            ElementType.HEADING,
            ElementType.LIST,
            ElementType.CAPTION,
        ):
            continue

        elem_tokens = estimate_tokens(elem.content)

        # Heading starts a new logical section.
        if elem.element_type == ElementType.HEADING:

            flush_chunk()

            current_section = elem.section

            parts = elem.section.split(" > ")

            current_parent = (
                " > ".join(parts[:-1])
                if len(parts) > 1
                else ""
            )

            current_page = elem.page_number

            current_parts.append(elem.content)
            current_tokens += elem_tokens

            continue

        # If a single element itself exceeds the chunk size,
        # split it rather than creating an oversized chunk.
        if elem_tokens > chunk_size:

            flush_chunk()

            words = elem.content.split()

            start = 0

            while start < len(words):

                end = min(
                    start + chunk_size,
                    len(words),
                )

                piece = " ".join(words[start:end])

                text_chunks.append(
                    TextChunkSchema(
                        document_id=document_id,
                        page_number=elem.page_number,
                        section=elem.section,
                        parent_section=current_parent,
                        content=piece,
                        chunk_type="text",
                        metadata={
                            "token_estimate": end - start,
                            "split_from_large_element": True,
                        },
                    )
                )

                step = max(
                    1,
                    chunk_size - overlap,
                )

                start += step

            current_parts = []
            current_tokens = 0

            current_page = elem.page_number
            current_section = elem.section

            continue

        if (
            current_tokens + elem_tokens > chunk_size
            and current_parts
        ):
            flush_chunk()

        current_parts.append(elem.content)
        current_tokens += elem_tokens

        current_page = elem.page_number

        if elem.section:
            current_section = elem.section

    flush_chunk()

    logger.info(
        "chunking_complete",
        text_chunks=len(text_chunks),
        table_chunks=len(table_chunks),
    )

    return text_chunks, table_chunks