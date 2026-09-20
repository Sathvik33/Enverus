import re

from app.schemas.document import ParsedElement, ElementType
from app.core.logging import get_logger


logger = get_logger(__name__)


TABLE_PATTERN = re.compile(
    r"(\|[^\n]+\|\n"
    r"(?:\|[-:| ]+\|\n)?"
    r"(?:\|[^\n]+\|\n?)+)",
    re.MULTILINE,
)

HEADING_PATTERN = re.compile(
    r"^(#{1,6})\s+(.+)$",
    re.MULTILINE,
)

CAPTION_PATTERN = re.compile(
    r"(?:^|\n)"
    r"((?:Figure|Fig\.|Table)\s+\d+[.:].+?)"
    r"(?:\n|$)",
    re.IGNORECASE,
)

LIST_PATTERN = re.compile(
    r"^[\s]*[-*•]\s+.+$",
    re.MULTILINE,
)


def _build_element(
    document_id: str,
    page_number: int,
    element_type: ElementType,
    section: str,
    content: str,
    metadata: dict | None = None,
) -> ParsedElement:
    return ParsedElement(
        document_id=document_id,
        page_number=page_number,
        element_type=element_type,
        section=section,
        content=content.strip(),
        metadata=metadata or {},
    )


def normalize_elements(
    document_id: str,
    parsed_data: dict,
) -> list[ParsedElement]:
    """
    Convert parser output into ordered ParsedElement objects.

    Important:
    Elements are emitted according to their original position
    in the page text rather than collecting all headings,
    tables, captions and paragraphs separately.
    """

    elements: list[ParsedElement] = []

    current_heading_stack: list[str] = []
    current_section = ""

    for chunk in parsed_data.get("page_chunks", []):
        metadata = chunk.get("metadata", {})

        page_number = metadata.get("page_number") or metadata.get("page") or 1

        if isinstance(page_number, int) and page_number <= 0:
            page_number = 1

        text = chunk.get("text", "")

        if not text or not text.strip():
            continue

        # normalize OCR and LaTeX numerals (e.g., 30 _._ 58 -> 30.58, 90 _._ 44% -> 90.44%)
        text = re.sub(r'(\d+)\s*_\._\s*(\d+)', r'\1.\2', text)
        text = re.sub(r'(\d+)\s*\.\s*_?(\d+)', r'\1.\2', text)
        text = re.sub(r'(\d+)\s+%', r'\1%', text)

        matches: list[tuple[int, int, str, re.Match]] = []

        for match in HEADING_PATTERN.finditer(text):
            matches.append(
                (
                    match.start(),
                    match.end(),
                    "heading",
                    match,
                )
            )

        for match in TABLE_PATTERN.finditer(text):
            matches.append(
                (
                    match.start(),
                    match.end(),
                    "table",
                    match,
                )
            )

        for match in CAPTION_PATTERN.finditer(text):
            matches.append(
                (
                    match.start(),
                    match.end(),
                    "caption",
                    match,
                )
            )

        # Sort all structural elements according to their actual
        # position in the source text.
        matches.sort(key=lambda item: item[0])

        cursor = 0

        for start, end, element_kind, match in matches:

            # Text before this structural element.
            before = text[cursor:start]

            if before.strip():
                elements.extend(
                    _normalize_text_block(
                        document_id=document_id,
                        page_number=page_number,
                        text=before,
                        section=current_section,
                    )
                )

            if element_kind == "heading":
                level = len(match.group(1))
                heading_text = match.group(2).strip()

                current_heading_stack = (
                    current_heading_stack[: level - 1]
                    + [heading_text]
                )

                current_section = " > ".join(
                    current_heading_stack
                )

                elements.append(
                    _build_element(
                        document_id=document_id,
                        page_number=page_number,
                        element_type=ElementType.HEADING,
                        section=current_section,
                        content=heading_text,
                        metadata={"level": level},
                    )
                )

            elif element_kind == "table":
                table_text = match.group(0).strip()

                elements.append(
                    _build_element(
                        document_id=document_id,
                        page_number=page_number,
                        element_type=ElementType.TABLE,
                        section=current_section,
                        content=table_text,
                        metadata={
                            "raw_markdown": table_text,
                        },
                    )
                )

            elif element_kind == "caption":
                caption = match.group(1).strip()

                elements.append(
                    _build_element(
                        document_id=document_id,
                        page_number=page_number,
                        element_type=ElementType.CAPTION,
                        section=current_section,
                        content=caption,
                    )
                )

            cursor = end

        # Remaining text after the final structural element.
        remaining = text[cursor:]

        if remaining.strip():
            elements.extend(
                _normalize_text_block(
                    document_id=document_id,
                    page_number=page_number,
                    text=remaining,
                    section=current_section,
                )
            )

    logger.info(
        "elements_normalized",
        total=len(elements),
        document_id=document_id,
    )

    return elements


def _normalize_text_block(
    document_id: str,
    page_number: int,
    text: str,
    section: str,
) -> list[ParsedElement]:

    results: list[ParsedElement] = []

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip()
    ]

    for paragraph in paragraphs:

        if len(paragraph) <= 10:
            continue

        is_list = bool(LIST_PATTERN.search(paragraph))

        results.append(
            _build_element(
                document_id=document_id,
                page_number=page_number,
                element_type=(
                    ElementType.LIST
                    if is_list
                    else ElementType.TEXT
                ),
                section=section,
                content=paragraph,
            )
        )

    return results