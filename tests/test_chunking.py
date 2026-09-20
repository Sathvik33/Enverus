import pytest
from app.ingestion.chunker import chunk_elements, estimate_tokens
from app.schemas.document import ParsedElement, ElementType


def _elem(content: str, etype: ElementType = ElementType.TEXT, page: int = 1, section: str = ""):
    return ParsedElement(document_id="doc-1", page_number=page, element_type=etype, section=section, content=content)


def test_estimate_tokens():
    assert estimate_tokens("hello world foo bar") == 4


def test_tables_remain_atomic():
    elements = [
        _elem("Intro text", ElementType.TEXT),
        _elem("| A | B |\n|---|---|\n| 1 | 2 |", ElementType.TABLE),
        _elem("More text", ElementType.TEXT),
    ]
    text_chunks, table_chunks = chunk_elements(elements, "doc-1")
    assert len(table_chunks) == 1
    assert "| A | B |" in table_chunks[0].table_content


def test_heading_creates_new_chunk():
    elements = [
        _elem("First paragraph. " * 50, ElementType.TEXT, section="Introduction"),
        _elem("New Section", ElementType.HEADING, section="New Section"),
        _elem("Second paragraph content.", ElementType.TEXT, section="New Section"),
    ]
    text_chunks, _ = chunk_elements(elements, "doc-1")
    assert len(text_chunks) >= 2


def test_empty_elements():
    text_chunks, table_chunks = chunk_elements([], "doc-1")
    assert text_chunks == []
    assert table_chunks == []


def test_chunk_preserves_section():
    elements = [_elem("Content in section", ElementType.TEXT, section="4.2 Results")]
    text_chunks, _ = chunk_elements(elements, "doc-1")
    assert text_chunks[0].section == "4.2 Results"
