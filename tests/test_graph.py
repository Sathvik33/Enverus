import pytest
from app.graph.state import RAGState
from app.guardrails.output_guardrail import validate_output


def test_rag_state_creation():
    state: RAGState = {
        "query": "What is DevAI?",
        "document_id": "test-123",
    }
    assert state["query"] == "What is DevAI?"


def test_output_guardrail_empty_answer():
    is_valid, answer, reason = validate_output("", [], "test query")
    assert not is_valid
    assert "sufficient" in answer.lower()


def test_output_guardrail_hedging():
    is_valid, answer, reason = validate_output(
        "I could not find sufficient evidence in the document.",
        [],
        "test query"
    )
    assert is_valid


def test_output_guardrail_valid():
    evidence = [{"content": "DevAI is a benchmark dataset containing 55 tasks for evaluating developer agents"}]
    answer = "DevAI is a benchmark dataset containing 55 tasks for evaluating developer agents."
    is_valid, cleaned, reason = validate_output(answer, evidence, "What is DevAI?")
    assert is_valid


def test_clean_output_artifacts_numbers():
    from app.guardrails.output_guardrail import clean_output_artifacts
    raw = "The score was 92 . 07% and 90._44%, with 70 . 76 % baseline."
    cleaned = clean_output_artifacts(raw)
    assert "92.07%" in cleaned
    assert "90.44%" in cleaned
    assert "70.76%" in cleaned


def test_clean_output_artifacts_citations():
    from app.guardrails.output_guardrail import clean_output_artifacts
    raw = "Found in [Page 1, Title > Chapter 4 > Section 4.2 Results, text_dense]."
    cleaned = clean_output_artifacts(raw)
    assert cleaned == "Found in [Page 1, Section 4.2 Results]."


def test_clean_section_and_format_label():
    from app.graph.nodes import _clean_section, _format_source_label
    assert _clean_section("**Doc Title** > **4 Method** > **4.2 Details**") == "4.2 Details"
    label = _format_source_label({
        "page_number": 3,
        "section": "A > B > 4.2 Details",
        "source_type": "text",
    })
    assert label == "[Page 3, Section 4.2 Details]"


def test_clean_output_artifacts_deduplication():
    from app.guardrails.output_guardrail import clean_output_artifacts
    raw = (
        "The DevAI dataset consists of 55 tasks designed to evaluate agentic systems in AI development.\n\n"
        "- **Direct Answer:**\n"
        "  The DevAI dataset contains 55 tasks, each tailored to assess an agentic system in AI development.\n\n"
        "- **Structured Details:**\n"
        "  - Number of Tasks: 55 [Page 1, Section 2.2]"
    )
    cleaned = clean_output_artifacts(raw)
    assert "- **Direct Answer:**" not in cleaned
    assert "- **Structured Details:**" not in cleaned
    assert "The DevAI dataset consists of 55 tasks" in cleaned
    assert "Number of Tasks: 55 [Page 1, Section 2.2]" in cleaned
    assert cleaned.count("55 tasks") == 2
