import pytest
from app.ingestion.normalizer import normalize_elements
from app.schemas.document import ElementType


def _make_page_chunks(text: str, page: int = 1):
    return {
        "page_chunks": [{"text": text, "metadata": {"page": page}}],
        "images_by_page": {},
        "page_count": 1,
    }


def test_normalize_extracts_headings():
    parsed = _make_page_chunks("# Introduction\nSome text about the topic.\n\n## Background\nMore details.")
    elements = normalize_elements("doc-1", parsed)
    headings = [e for e in elements if e.element_type == ElementType.HEADING]
    assert len(headings) >= 2
    assert any("Introduction" in h.content for h in headings)


def test_normalize_extracts_tables():
    table_md = "| System | Cost |\n|---|---|\n| GPT | $5.00 |\n| Claude | $3.00 |"
    parsed = _make_page_chunks(f"Some text.\n\n{table_md}\n\nMore text.")
    elements = normalize_elements("doc-1", parsed)
    tables = [e for e in elements if e.element_type == ElementType.TABLE]
    assert len(tables) >= 1
    assert "GPT" in tables[0].content


def test_normalize_extracts_captions():
    parsed = _make_page_chunks("Some text.\n\nFigure 1: Overview of the system architecture.\n\nMore text.")
    elements = normalize_elements("doc-1", parsed)
    captions = [e for e in elements if e.element_type == ElementType.CAPTION]
    assert len(captions) >= 1


def test_normalize_preserves_page_numbers():
    parsed = _make_page_chunks("# Section\nContent here.", page=5)
    elements = normalize_elements("doc-1", parsed)
    assert all(e.page_number == 5 for e in elements)


def test_normalize_empty_input():
    parsed = {"page_chunks": [], "images_by_page": {}, "page_count": 0}
    elements = normalize_elements("doc-1", parsed)
    assert elements == []
