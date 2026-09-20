import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.workflow import answer_query
from app.db.database import init_db
from app.core.logging import setup_logging, get_logger

EVAL_QUESTIONS = [
    {"question": "What is the DevAI dataset and how many tasks does it contain?", "expected_page": [4, 5], "type": "factual_text"},
    {"question": "What is the Agent-as-a-Judge framework and how does it work?", "expected_page": [1, 2], "type": "factual_text"},
    {"question": "What was the cost and time for Human-as-a-Judge evaluation?", "expected_page": [8, 9, 10], "type": "numerical"},
    {"question": "What open-source developer agents were evaluated?", "expected_page": [6, 7], "type": "factual_text"},
    {"question": "What was the average cost of OpenHands?", "expected_page": [8, 9, 10], "type": "numerical"},
    {"question": "Which was the most expensive system evaluated?", "expected_page": [8, 9, 10], "type": "table"},
    {"question": "What was GPT-Pilot's requirements met rate?", "expected_page": [8, 9, 10], "type": "numerical"},
    {"question": "What was MetaGPT's task solve rate?", "expected_page": [8, 9, 10], "type": "numerical"},
    {"question": "What was OpenHands alignment rate with human judges?", "expected_page": [8, 9, 10], "type": "numerical"},
    {"question": "What components were studied in the ablation analysis?", "expected_page": [10, 11], "type": "factual_text"},
    {"question": "What search algorithms were compared in the paper?", "expected_page": [5, 6], "type": "factual_text"},
    {"question": "What model architectures are discussed in DevAI?", "expected_page": [4, 5], "type": "factual_text"},
    {"question": "What is requirement R1 in the DevAI dataset?", "expected_page": [4, 5], "type": "factual_text"},
    {"question": "What types of errors did human evaluators make?", "expected_page": [9, 10, 11], "type": "factual_text"},
    {"question": "What does Figure 1 show about the three judge approaches?", "expected_page": [1, 2], "type": "figure"},
]


async def run_evaluation(document_id: str):
    setup_logging()
    logger = get_logger("evaluate")
    await init_db()

    results = []
    total = len(EVAL_QUESTIONS)

    for i, q in enumerate(EVAL_QUESTIONS):
        print(f"\n[{i+1}/{total}] {q['question']}")
        try:
            response = await answer_query(document_id, q["question"])
            answer = response.get("answer", "")
            evidence = response.get("evidence", [])
            citations = response.get("citations", [])
            trace = response.get("retrieval_trace", {})

            retrieved_pages = set()
            for e in evidence:
                if isinstance(e, dict):
                    retrieved_pages.add(e.get("page_number", 0))
                else:
                    retrieved_pages.add(getattr(e, "page_number", 0))

            page_hit = bool(retrieved_pages & set(q["expected_page"]))
            has_evidence = len(evidence) > 0
            has_citations = len(citations) > 0
            not_hedging = "could not find" not in answer.lower()

            result = {
                "question": q["question"],
                "type": q["type"],
                "answer_preview": answer[:200],
                "page_hit": page_hit,
                "has_evidence": has_evidence,
                "has_citations": has_citations,
                "answered": not_hedging,
                "retrieved_pages": list(retrieved_pages),
                "expected_pages": q["expected_page"],
                "evidence_count": len(evidence),
            }
            results.append(result)

            status = "✅" if (page_hit and has_evidence and not_hedging) else "❌"
            print(f"  {status} Pages: {retrieved_pages} | Evidence: {len(evidence)} | Answered: {not_hedging}")
            print(f"  Answer: {answer[:150]}...")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "question": q["question"],
                "type": q["type"],
                "error": str(e),
                "page_hit": False,
                "has_evidence": False,
                "has_citations": False,
                "answered": False,
            })

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    metrics = {
        "total": total,
        "page_hits": sum(1 for r in results if r.get("page_hit")),
        "has_evidence": sum(1 for r in results if r.get("has_evidence")),
        "has_citations": sum(1 for r in results if r.get("has_citations")),
        "answered": sum(1 for r in results if r.get("answered")),
    }

    for key, val in metrics.items():
        if key == "total":
            print(f"  Total Questions: {val}")
        else:
            print(f"  {key}: {val}/{total} ({val/total*100:.1f}%)")

    output_path = Path("data/evaluation_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"metrics": metrics, "results": results}, f, indent=2, default=str)
    print(f"\nDetailed results saved to {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate the RAG system")
    parser.add_argument("--document-id", required=True, help="Document ID to evaluate against")
    args = parser.parse_args()
    asyncio.run(run_evaluation(args.document_id))
