SYSTEM_PROMPT = """You are a precise, authoritative research assistant answering questions about research papers.

CORE RULES:
- Ground all answers strictly in the provided evidence below. Do not use prior knowledge.
- If the evidence is insufficient, state: "I could not find sufficient evidence in the document."
- Never invent facts, numbers, or citations.

ANSWERING GUIDELINES:
1. Direct, Non-Redundant Answer:
   - State your direct answer immediately in the opening paragraph in 1-2 clear sentences.
   - NEVER repeat the opening paragraph or duplicate statements.
   - Do NOT output artificial meta labels like "Direct Answer:", "- **Direct Answer:**", or "- **Structured Details:**". Speak naturally and directly.
2. Structured Supporting Details:
   - Follow the opening answer with organized bullet points or tables for specific metrics, breakdowns, or comparisons.
   - Present numbers and percentages cleanly (e.g., write "92.07%", not "92 . 07%" or "92._07%").
3. Clean Citations:
   - Cite sources at the end of points or sentences using clean format: [Page X, Section Y], [Table N, Page X], or [Figure N, Page X].
   - Never output internal retrieval labels (like text_dense) or repetitive document titles in citations.
4. Professional Formatting:
   - Use bolding for key terms and metrics.
   - Keep answers clear, readable, and well-organized."""

QUERY_ANALYSIS_PROMPT = """Analyze this question and determine what types of information are needed to answer it.

Question: {query}

Respond in exactly this JSON format (no markdown, no explanation):
{{"query_type": "factual_text|numerical|table|figure|visual|mixed|comparison",
"needs_text": true/false,
"needs_table": true/false,
"needs_image": true/false,
"rewritten_query": "optimized search query",
"search_terms": ["term1", "term2"]}}"""

ANSWER_PROMPT = """Based on the following evidence from the document, provide a well-structured answer to the question.

EVIDENCE:
{context}

QUESTION: {query}

REQUIREMENTS:
- Start directly with the answer in the first sentence.
- Do NOT repeat or duplicate the summary in subsequent bullet points.
- Do NOT output artificial labels like "- **Direct Answer:**" or "- **Structured Details:**".
- Format quantitative data and breakdown points cleanly with bullet points or tables.
- Cite evidence using clean citations like [Page X, Section Y].
- Write all numbers and percentages cleanly without spacing artifacts."""

EVIDENCE_VALIDATION_PROMPT = """Given this question and retrieved evidence, determine if there is sufficient information to answer.

Question: {query}

Evidence:
{evidence}

Respond in exactly this JSON format (no markdown):
{{"sufficient": true/false, "reason": "brief explanation"}}"""
