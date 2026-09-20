import pytest
from app.schemas.chat import ChatRequest, ChatResponse, Citation, Evidence


def test_chat_request_validation():
    req = ChatRequest(document_id="test-123", query="What is DevAI?")
    assert req.query == "What is DevAI?"


def test_chat_response_creation():
    resp = ChatResponse(
        answer="DevAI is a benchmark.",
        citations=[Citation(page_number=5, section="Dataset", source_type="text")],
        evidence=[Evidence(id="e1", content="DevAI benchmark", score=0.95, page_number=5)],
    )
    assert resp.answer == "DevAI is a benchmark."
    assert len(resp.citations) == 1
    assert resp.citations[0].page_number == 5


def test_citation_format():
    c = Citation(page_number=10, section="4.2 Results", source_type="table", source_id="chunk-1")
    assert c.page_number == 10
    assert c.source_type == "table"
