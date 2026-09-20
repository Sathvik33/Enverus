import re
from app.guardrails.pii import detect_pii
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

HEDGING_PHRASES = [
    "Not enough information in the PDF",
    "not enough information in the pdf",
    "not enough information",
    "I could not find sufficient evidence",
    "insufficient evidence",
    "no relevant evidence",
]


def clean_output_artifacts(text: str) -> str:
    if not text:
        return text

    # normalize OCR and LaTeX spacing in numbers
    text = re.sub(r'(\d+)\s*_\._\s*(\d+)', r'\1.\2', text)
    text = re.sub(r'(\d+)\s*\.\s*_?(\d+)', r'\1.\2', text)
    text = re.sub(r'(\d+)\s+%', r'\1%', text)

    # strip stray underscores around digits
    text = re.sub(r'(?<=\s)_+(\d+)', r'\1', text)
    text = re.sub(r'(\d+)_+(?=\s|[.,;:]|$)', r'\1', text)

    # remove internal retrieval labels from citation brackets
    text = re.sub(r',\s*(?:text_dense|text_bm25|table_dense|image_dense|dense|bm25)\b', '', text)

    # simplify section hierarchy breadcrumbs inside citation brackets
    def _simplify_bracket(match):
        inner = match.group(1)
        if " > " in inner:
            parts = inner.split(" > ")
            deepest = parts[-1].strip()
            m_prefix = re.match(r"^(Page\s+\d+,\s*)", parts[0])
            if m_prefix:
                return f"[{m_prefix.group(1)}{deepest}]"
            return f"[{deepest}]"
        return match.group(0)

    text = re.sub(r'\[([^\]]+)\]', _simplify_bracket, text)

    # Strip artificial meta headers and eliminate duplicate summary blocks
    blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
    cleaned_blocks = []
    for b in blocks:
        m_meta = re.match(r'^[-*]?\s*\*\*(?:Direct Answer|Structured Details|Answer):\*\*\s*(.*)', b, re.IGNORECASE | re.DOTALL)
        if m_meta:
            content = m_meta.group(1).strip()
            if not content:
                continue
            if cleaned_blocks:
                words_p = set(re.findall(r'\w{3,}', cleaned_blocks[-1].lower()))
                words_c = set(re.findall(r'\w{3,}', content.lower()))
                if words_p and words_c:
                    overlap = len(words_p & words_c) / min(len(words_p), len(words_c))
                    if overlap > 0.65:
                        continue
            b = content
        cleaned_blocks.append(b)

    text = '\n\n'.join(cleaned_blocks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def validate_output(answer: str, evidence: list[dict], query: str) -> tuple[bool, str, str]:
    settings = get_settings()

    if not answer or not answer.strip():
        return False, "Not enough information in the PDF.", "Empty answer"

    for phrase in HEDGING_PHRASES:
        if phrase.lower() in answer.lower():
            return True, "Not enough information in the PDF.", "Model indicated insufficient evidence"

    if settings.OUTPUT_GROUNDING_ENABLED and evidence:
        evidence_text = " ".join(e.get("content", "") for e in evidence).lower()

        # Extract meaningful tokens (words, numbers, percentages) from answer
        tokens = re.findall(r'[A-Za-z0-9.%$]+', answer.lower())
        meaningful = [t for t in tokens if len(t) >= 3 or any(c.isdigit() for c in t)]

        if meaningful:
            overlap = sum(1 for t in meaningful if t in evidence_text)
            grounding_ratio = overlap / len(meaningful)
            if grounding_ratio < 0.25:
                logger.warning("low_grounding_score", ratio=grounding_ratio)
                return False, "Not enough information in the PDF.", f"Low grounding: {grounding_ratio:.2f}"

    if settings.PII_DETECTION_ENABLED:
        pii = detect_pii(answer)
        if pii:
            logger.warning("pii_in_output", count=len(pii))
            from app.guardrails.pii import anonymize_text
            answer = anonymize_text(answer)

    cleaned_answer = clean_output_artifacts(answer)
    return True, cleaned_answer, "OK"
