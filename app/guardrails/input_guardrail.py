from app.guardrails.pii import detect_pii, anonymize_text
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_input(query: str) -> tuple[str, list[dict]]:
    """Validate and sanitize user input, returns cleaned query and any PII findings."""
    settings = get_settings()

    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    if len(query) > 5000:
        raise ValueError("Query exceeds maximum length of 5000 characters")

    cleaned = query.strip()
    pii_findings = []

    if settings.PII_DETECTION_ENABLED:
        pii_findings = detect_pii(cleaned)
        if pii_findings:
            logger.warning("pii_detected_in_input", count=len(pii_findings))
            cleaned = anonymize_text(cleaned)

    return cleaned, pii_findings
