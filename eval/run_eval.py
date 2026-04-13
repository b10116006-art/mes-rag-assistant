"""
Phase 4: Local evaluation utility for the MES RAG Assistant.

Runs a small labeled dataset through the existing analysis path and reports
three accuracy metrics:
  - anomaly_type_accuracy  (LLM decision quality)
  - memory_used_accuracy   (memory retrieval correctness)
  - route_used_accuracy    (Phase 3 routing correctness)

Routing and memory metrics are computed directly via the helper functions
in app.py, so they remain meaningful even if no LLM API key is configured
(in that case, anomaly_type_accuracy will simply be 0).

Usage:
  python eval/run_eval.py

Outputs:
  - Console summary + per-case table
  - eval/eval_results.json  (full detail, for diffing across runs)
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import (  # noqa: E402
    build_rag_system,
    run_analysis_with_mode,
    retrieve_memory,
    route_query,
)

CASES_PATH = Path(__file__).parent / "eval_cases.json"
RESULTS_PATH = Path(__file__).parent / "eval_results.json"
RATE_LIMIT_SLEEP = 2.1  # app.rate_limit() rejects calls within 2s


def load_cases(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_case(case: dict) -> dict:
    query = case["query"]

    mem_records = retrieve_memory(query)
    mem_hit = len(mem_records) > 0
    route_used, decision_reason, qclass = route_query(query, mem_hit)

    time.sleep(RATE_LIMIT_SLEEP)
    raw = run_analysis_with_mode(query, mode="auto")

    predicted_type = None
    validation_passed = None
    llm_ok = False
    parsed_route = route_used
    parsed_memory = mem_hit

    try:
        parsed = json.loads(raw)
        predicted_type = parsed.get("anomaly_type")
        validation_passed = parsed.get("validation_passed")
        parsed_route = parsed.get("route_used", route_used)
        parsed_memory = parsed.get("memory_used", mem_hit)
        llm_ok = predicted_type is not None
    except Exception:
        pass

    return {
        "id": case.get("id"),
        "tag": case.get("tag"),
        "query": query,
        "query_class": qclass,
        "decision_reason": decision_reason,
        "expected_anomaly_type": case["expected_anomaly_type"],
        "predicted_anomaly_type": predicted_type,
        "expected_memory_used": case["expected_memory_used"],
        "actual_memory_used": parsed_memory,
        "expected_route_used": case["expected_route_used"],
        "actual_route_used": parsed_route,
        "validation_passed": validation_passed,
        "llm_ok": llm_ok,
    }


def compute_summary(results: list) -> dict:
    total = len(results)
    if total == 0:
        return {"total_cases": 0}
    type_correct = sum(
        1 for r in results if r["predicted_anomaly_type"] == r["expected_anomaly_type"]
    )
    mem_correct = sum(
        1 for r in results if r["actual_memory_used"] == r["expected_memory_used"]
    )
    route_correct = sum(
        1 for r in results if r["actual_route_used"] == r["expected_route_used"]
    )
    llm_ok = sum(1 for r in results if r["llm_ok"])
    return {
        "total_cases": total,
        "llm_responses_parsed": llm_ok,
        "anomaly_type_accuracy": round(type_correct / total, 3),
        "memory_used_accuracy": round(mem_correct / total, 3),
        "route_used_accuracy": round(route_correct / total, 3),
    }


def print_report(summary: dict, results: list) -> None:
    bar = "=" * 60
    print("\n" + bar)
    print("PHASE 4 EVALUATION SUMMARY")
    print(bar)
    for k, v in summary.items():
        print(f"  {k:<25} {v}")
    print(bar)

    print(f"\n{'#':<4}{'mem':<5}{'route':<7}{'type':<6}{'tag':<13}query")
    print("-" * 78)
    for i, r in enumerate(results, 1):
        mem_ok = "OK" if r["actual_memory_used"] == r["expected_memory_used"] else "FAIL"
        route_ok = "OK" if r["actual_route_used"] == r["expected_route_used"] else "FAIL"
        type_ok = (
            "OK" if r["predicted_anomaly_type"] == r["expected_anomaly_type"] else "FAIL"
        )
        q = r["query"][:40]
        print(f"{i:<4}{mem_ok:<5}{route_ok:<7}{type_ok:<6}{r['tag'] or '':<13}{q}")
    print()


def main() -> int:
    cases = load_cases(CASES_PATH)
    print(f"Loaded {len(cases)} evaluation cases from {CASES_PATH}")

    print("Building RAG system (one-time initialization)...")
    build_rag_system()
    print("RAG system ready. Running evaluation...")

    results = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case.get('id')} — {case['query'][:55]}")
        results.append(evaluate_case(case))

    summary = compute_summary(results)
    print_report(summary, results)

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f, ensure_ascii=False, indent=2)
    print(f"Detailed results saved to: {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
