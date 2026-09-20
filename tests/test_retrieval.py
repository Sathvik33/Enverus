import pytest
from app.ingestion.table_processor import parse_markdown_table, table_to_text_representation
from app.guardrails.pii import detect_pii, anonymize_text
from app.guardrails.input_guardrail import validate_input


def test_parse_markdown_table():
    table = "| System | Cost | Time |\n|---|---|---|\n| GPT | $5.00 | 10min |\n| Claude | $3.00 | 8min |"
    result = parse_markdown_table(table)
    assert result["headers"] == ["System", "Cost", "Time"]
    assert len(result["rows"]) == 2
    assert result["row_count"] == 2


def test_table_to_text():
    data = {"headers": ["System", "Cost"], "rows": [["GPT", "$5.00"], ["Claude", "$3.00"]]}
    text = table_to_text_representation(data, "Results", 10)
    assert "System" in text
    assert "GPT" in text
    assert "$5.00" in text


def test_detect_pii_email():
    findings = detect_pii("Contact me at test@example.com for info.")
    assert len(findings) == 1
    assert findings[0]["type"] == "EMAIL"


def test_detect_pii_phone():
    findings = detect_pii("Call 555-123-4567 for support.")
    assert len(findings) >= 1


def test_anonymize():
    result = anonymize_text("Email me at user@test.com and call 555-123-4567.")
    assert "[EMAIL]" in result
    assert "user@test.com" not in result


def test_input_guardrail_empty():
    with pytest.raises(ValueError):
        validate_input("")


def test_input_guardrail_strips():
    cleaned, pii = validate_input("  Hello world  ")
    assert cleaned == "Hello world"
    assert pii == []
