import re

PII_PATTERNS = {
    "EMAIL": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    "PHONE": re.compile(r'(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}'),
    "SSN": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "CREDIT_CARD": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    "IP_ADDRESS": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
}


def detect_pii(text: str) -> list[dict]:
    findings = []
    for pii_type, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append({
                "type": pii_type,
                "value": match.group(),
                "start": match.start(),
                "end": match.end(),
            })
    return findings


def anonymize_text(text: str) -> str:
    result = text
    for pii_type, pattern in PII_PATTERNS.items():
        result = pattern.sub(f"[{pii_type}]", result)
    return result
