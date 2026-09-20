import re
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
    """
    if not text:
        return 0
    return len(text.split())


def split_into_sentences(text: str) -> list[str]:
    """
    Split text into sentences while keeping list-introducing clauses intact.
    If a sentence ends with a colon, dash, or introductory phrase (e.g. 'including:', 'frameworks:'),
    keep it connected with the following list.
    """
    if not text:
        return []

    raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\'\(\[])', text)
    sentences = []
    buffer = ""

    for s in raw_sentences:
        s = s.strip()
        if not s:
            continue
        if buffer:
            buffer += " " + s
        else:
            buffer = s

        # Keep introductory list clauses attached to their items
        if buffer.endswith(":") or buffer.endswith(":-") or re.search(r'\b(?:such as|including|namely|e\.g\.|i\.e\.|frameworks|baselines|models)\s*$', buffer, re.I):
            continue

        sentences.append(buffer)
        buffer = ""

    if buffer:
        sentences.append(buffer)

    return sentences if sentences else [text]


def _take_last_sentences(
    parts: list[str],
    max_tokens: int,
) -> tuple[list[str], int]:
    """
    Extract trailing complete sentences for chunk overlap, never slicing words mid-sentence.
    """
    if max_tokens <= 0 or not parts:
        return [], 0

    all_sentences = []
    for p in parts:
        all_sentences.extend(split_into_sentences(p))

    overlap_sentences = []
    total_tokens = 0

    for sent in reversed(all_sentences):
        sent_tokens = estimate_tokens(sent)
        if total_tokens + sent_tokens <= max_tokens or not overlap_sentences:
            overlap_sentences.insert(0, sent)
            total_tokens += sent_tokens
        else:
            break

    return overlap_sentences, total_tokens


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
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")

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

        overlap_parts, overlap_tokens = _take_last_sentences(
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
            current_parent = " > ".join(parts[:-1]) if len(parts) > 1 else ""
            current_page = elem.page_number
            current_parts.append(elem.content)
            current_tokens += elem_tokens
            continue

        # If a single element exceeds chunk size, split cleanly along sentence boundaries
        if elem_tokens > chunk_size:
            flush_chunk()
            sentences = split_into_sentences(elem.content)
            group: list[str] = []
            group_tokens = 0

            for sent in sentences:
                sent_tokens = estimate_tokens(sent)
                if group_tokens + sent_tokens > chunk_size and group:
                    text_chunks.append(
                        TextChunkSchema(
                            document_id=document_id,
                            page_number=elem.page_number,
                            section=elem.section,
                            parent_section=current_parent,
                            content=" ".join(group).strip(),
                            chunk_type="text",
                            metadata={
                                "token_estimate": group_tokens,
                                "split_from_large_element": True,
                            },
                        )
                    )
                    overlap_group, overlap_group_tokens = _take_last_sentences(group, overlap)
                    group = list(overlap_group)
                    group_tokens = overlap_group_tokens

                group.append(sent)
                group_tokens += sent_tokens

            if group:
                current_parts = group
                current_tokens = group_tokens
                current_page = elem.page_number
                current_section = elem.section
            continue

        if current_tokens + elem_tokens > chunk_size and current_parts:
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