"""
Phase B: Live evaluation utility for the MES RAG Assistant.

Supports two modes controlled by USE_LIVE_LLM:
  True  — calls the real LLM stack via app.run_analysis_with_mode()
  False — skips LLM calls; only evaluates memory/routing/retrieval signals

When live, runs a 4-mode A/B grid over query rewrite × rerank, prints a
comparison table, and appends a short interpretation block.

Usage:
  python eval/run_eval.py              # USE_LIVE_LLM from env, default True
  USE_LIVE_LLM=0 python eval/run_eval.py   # offline-only mode

Outputs:
  - Console summary + per-case table + A/B comparison + interpretation
  - eval/eval_results.json  (full detail for the last mode run)
"""

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import app as app_module  # noqa: E402  — module ref for flag mutation
from app import (  # noqa: E402
    build_rag_system,
    run_analysis_with_mode,
    retrieve_memory,
    route_query,
)

CASES_PATH = Path(__file__).parent / "eval_cases.json"
RESULTS_PATH = Path(__file__).parent / "eval_results.json"
AB_RESULTS_PATH = Path(__file__).parent / "eval_ab_results.json"
RATE_LIMIT_SLEEP = 2.1  # app.rate_limit() rejects calls within 2s
TOP_K = 3

USE_LIVE_LLM = os.environ.get("USE_LIVE_LLM", "1") not in ("0", "false", "False")

# Phase B A/B grid: (mode_name, use_rewrite, use_rerank)
AB_MODES = [
    ("baseline",     False, False),
    ("rewrite_only", True,  False),
    ("rerank_only",  False, True),
    ("full",         True,  True),
]


def load_cases(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _action_match_score(expected_actions, predicted_actions):
    """Keyword-overlap scoring: fraction of expected actions whose key terms appear in predictions."""
    if not expected_actions:
        return None
    if not predicted_actions:
        return 0.0
    pred_pool = " ".join(predicted_actions).lower()
    matched = 0
    for ea in expected_actions:
        tokens = set(ea.lower().split()) - {""}
        if not tokens:
            continue
        hit_ratio = sum(1 for t in tokens if t in pred_pool) / len(tokens)
        if hit_ratio >= 0.5:
            matched += 1
    return round(matched / len(expected_actions), 3)


def _set_ab_flags(use_rewrite: bool, use_rerank: bool):
    """Mutate app-module flags if they exist; silently skip if they don't."""
    if hasattr(app_module, "USE_QUERY_REWRITE"):
        app_module.USE_QUERY_REWRITE = use_rewrite
    if hasattr(app_module, "USE_RERANK"):
        app_module.USE_RERANK = use_rerank


def evaluate_case(case: dict, mode_name: str = "single") -> dict:
    query = case["query"]

    mem_records = retrieve_memory(query)
    mem_hit = len(mem_records) > 0
    route_used, decision_reason, qclass = route_query(query, mem_hit)

    predicted_type = None
    validation_passed = None
    llm_ok = False
    parsed_route = route_used
    parsed_memory = mem_hit
    top_sources = []
    predicted_actions = []
    retrieved_count = None
    reranked_count = None
    raw_answer = None
    call_success = False

    if USE_LIVE_LLM:
        time.sleep(RATE_LIMIT_SLEEP)
        try:
            raw = run_analysis_with_mode(query, mode="auto")
            raw_answer = raw
            parsed = json.loads(raw)
            predicted_type = parsed.get("anomaly_type")
            validation_passed = parsed.get("validation_passed")
            parsed_route = parsed.get("route_used", route_used)
            parsed_memory = parsed.get("memory_used", mem_hit)
            top_sources = parsed.get("top_sources", []) or []
            predicted_actions = parsed.get("recommended_actions", []) or []
            retrieved_count = parsed.get("retrieved_count")
            reranked_count = parsed.get("reranked_count")
            llm_ok = predicted_type is not None
            call_success = llm_ok
        except Exception as e:
            raw_answer = str(e)

    expected_sources = case.get("expected_sources")
    if not expected_sources:
        retrieval_hit = None
        top_k_hit = None
        source_overlap = None
        retrieval_recall = None
    else:
        expected_set = set(expected_sources)
        retrieval_hit = bool(expected_set & set(top_sources))
        top_k_slice = set(top_sources[:TOP_K])
        top_k_hit = bool(expected_set & top_k_slice)
        source_overlap = len(expected_set & top_k_slice)
        retrieval_recall = round(len(expected_set & set(top_sources)) / len(expected_set), 3)

    type_score = 1.0 if predicted_type == case["expected_anomaly_type"] else 0.0
    expected_actions = case.get("expected_actions")
    action_score = _action_match_score(expected_actions, predicted_actions)
    if action_score is not None:
        decision_match_score = round(0.5 * type_score + 0.5 * action_score, 3)
    else:
        decision_match_score = type_score

    return {
        "mode": mode_name,
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
        "call_success": call_success,
        "expected_sources": expected_sources,
        "top_sources": top_sources,
        "retrieved_count": retrieved_count,
        "reranked_count": reranked_count,
        "retrieval_hit": retrieval_hit,
        "top_k_hit": top_k_hit,
        "source_overlap": source_overlap,
        "retrieval_recall": retrieval_recall,
        "decision_match_score": decision_match_score,
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
    call_ok = sum(1 for r in results if r.get("call_success"))

    retrieval_graded = [r for r in results if r.get("retrieval_hit") is not None]
    retrieval_total = len(retrieval_graded)
    if retrieval_total > 0:
        retrieval_hit_rate = round(
            sum(1 for r in retrieval_graded if r["retrieval_hit"]) / retrieval_total, 3
        )
        top_k_hit_rate = round(
            sum(1 for r in retrieval_graded if r["top_k_hit"]) / retrieval_total, 3
        )
        avg_source_overlap = round(
            sum(r["source_overlap"] for r in retrieval_graded) / retrieval_total, 3
        )
    else:
        retrieval_hit_rate = None
        top_k_hit_rate = None
        avg_source_overlap = None

    retrieved_values = [r["retrieved_count"] for r in results if r.get("retrieved_count") is not None]
    reranked_values = [r["reranked_count"] for r in results if r.get("reranked_count") is not None]
    avg_retrieved = round(sum(retrieved_values) / len(retrieved_values), 2) if retrieved_values else None
    avg_reranked = round(sum(reranked_values) / len(reranked_values), 2) if reranked_values else None

    recall_values = [r["retrieval_recall"] for r in results if r.get("retrieval_recall") is not None]
    avg_retrieval_recall = round(sum(recall_values) / len(recall_values), 3) if recall_values else None

    dm_values = [r["decision_match_score"] for r in results if r.get("decision_match_score") is not None]
    avg_decision_match = round(sum(dm_values) / len(dm_values), 3) if dm_values else None

    return {
        "total_cases": total,
        "llm_responses_parsed": llm_ok,
        "call_success_count": call_ok,
        "anomaly_type_accuracy": round(type_correct / total, 3),
        "memory_used_accuracy": round(mem_correct / total, 3),
        "route_used_accuracy": round(route_correct / total, 3),
        "retrieval_graded_cases": retrieval_total,
        "retrieval_hit_rate": retrieval_hit_rate,
        "top_k_hit_rate": top_k_hit_rate,
        "avg_source_overlap": avg_source_overlap,
        "avg_retrieved_count": avg_retrieved,
        "avg_reranked_count": avg_reranked,
        "avg_retrieval_recall": avg_retrieval_recall,
        "avg_decision_match": avg_decision_match,
    }


def print_report(summary: dict, results: list) -> None:
    bar = "=" * 60
    print("\n" + bar)
    print("EVALUATION SUMMARY")
    print(bar)
    for k, v in summary.items():
        print(f"  {k:<25} {v}")
    print(bar)

    print(f"\n{'#':<4}{'mem':<5}{'route':<7}{'type':<6}{'retr':<6}{'ovlp':<6}{'tag':<13}query")
    print("-" * 96)
    for i, r in enumerate(results, 1):
        mem_ok = "OK" if r["actual_memory_used"] == r["expected_memory_used"] else "FAIL"
        route_ok = "OK" if r["actual_route_used"] == r["expected_route_used"] else "FAIL"
        type_ok = "OK" if r["predicted_anomaly_type"] == r["expected_anomaly_type"] else "FAIL"
        if r.get("retrieval_hit") is None:
            retr_ok = "-"
            ovlp = "-"
        else:
            retr_ok = "OK" if r["retrieval_hit"] else "FAIL"
            ovlp = str(r["source_overlap"])
        q = r["query"][:40]
        print(f"{i:<4}{mem_ok:<5}{route_ok:<7}{type_ok:<6}{retr_ok:<6}{ovlp:<6}{r['tag'] or '':<13}{q}")
    print()


def run_mode(mode_name: str, use_rewrite: bool, use_rerank: bool, cases: list) -> dict:
    _set_ab_flags(use_rewrite, use_rerank)
    bar = "=" * 60
    print(f"\n{bar}\nMODE: {mode_name}  (rewrite={use_rewrite}, rerank={use_rerank})\n{bar}")
    results = []
    for i, case in enumerate(cases, 1):
        print(f"  [{mode_name} {i}/{len(cases)}] {case.get('id')} — {case['query'][:45]}")
        results.append(evaluate_case(case, mode_name=mode_name))
    summary = compute_summary(results)
    return {"mode": mode_name, "use_rewrite": use_rewrite, "use_rerank": use_rerank,
            "summary": summary, "results": results}


def _fmt(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def print_ab_comparison(mode_runs: list) -> None:
    bar = "=" * 98
    print("\n" + bar)
    print("A/B COMPARISON — retrieval & decision metrics by mode")
    print(bar)
    header = (f"{'MODE':<14}{'RECALL':<9}{'TOPK':<8}{'OVERLAP':<9}"
              f"{'DEC_MATCH':<11}{'TYPE_ACC':<10}{'RETR':<7}{'RERANK':<8}{'LLM_OK':<8}")
    print(header)
    print("-" * 98)
    for run in mode_runs:
        s = run["summary"]
        row = (
            f"{run['mode']:<14}"
            f"{_fmt(s.get('avg_retrieval_recall')):<9}"
            f"{_fmt(s.get('top_k_hit_rate')):<8}"
            f"{_fmt(s.get('avg_source_overlap')):<9}"
            f"{_fmt(s.get('avg_decision_match')):<11}"
            f"{_fmt(s.get('anomaly_type_accuracy')):<10}"
            f"{_fmt(s.get('avg_retrieved_count')):<7}"
            f"{_fmt(s.get('avg_reranked_count')):<8}"
            f"{s.get('call_success_count', 0)}/{s.get('total_cases', 0)}"
        )
        print(row)
    print(bar)


def print_interpretation(mode_runs: list) -> None:
    by_name = {r["mode"]: r["summary"] for r in mode_runs}
    bar = "-" * 60
    print(f"\n{bar}")
    print("INTERPRETATION")
    print(bar)

    def _get(name, key):
        v = by_name.get(name, {}).get(key)
        return v if isinstance(v, (int, float)) else None

    base_topk = _get("baseline", "top_k_hit_rate")
    rw_topk = _get("rewrite_only", "top_k_hit_rate")
    rr_topk = _get("rerank_only", "top_k_hit_rate")
    full_topk = _get("full", "top_k_hit_rate")

    base_type = _get("baseline", "anomaly_type_accuracy")
    full_type = _get("full", "anomaly_type_accuracy")

    if base_topk is not None and full_topk is not None:
        delta = full_topk - base_topk
        if delta > 0.01:
            print(f"  Full mode improved top_k_hit_rate by +{delta:.3f} over baseline.")
        elif delta < -0.01:
            print(f"  Full mode DEGRADED top_k_hit_rate by {delta:.3f} vs baseline.")
        else:
            print("  Full mode vs baseline: top_k_hit_rate is flat (no measurable change).")

    if rw_topk is not None and rr_topk is not None and base_topk is not None:
        rw_delta = (rw_topk - base_topk) if base_topk is not None else None
        rr_delta = (rr_topk - base_topk) if base_topk is not None else None
        if rw_delta is not None and rr_delta is not None:
            if rw_delta > rr_delta + 0.01:
                print(f"  Query rewrite contributed more (+{rw_delta:.3f}) than rerank (+{rr_delta:.3f}).")
            elif rr_delta > rw_delta + 0.01:
                print(f"  Rerank contributed more (+{rr_delta:.3f}) than query rewrite (+{rw_delta:.3f}).")
            else:
                print(f"  Rewrite (+{rw_delta:.3f}) and rerank (+{rr_delta:.3f}) contributed roughly equally.")

    if base_type is not None and full_type is not None:
        t_delta = full_type - base_type
        if abs(t_delta) < 0.01:
            print(f"  anomaly_type_accuracy: no significant change ({base_type:.3f} → {full_type:.3f}).")
        else:
            direction = "improved" if t_delta > 0 else "degraded"
            print(f"  anomaly_type_accuracy {direction}: {base_type:.3f} → {full_type:.3f} ({t_delta:+.3f}).")

    if base_topk is None and rw_topk is None:
        print("  Retrieval metrics unavailable — eval cases lack expected_sources labels.")

    if not USE_LIVE_LLM:
        print("  NOTE: USE_LIVE_LLM=False — LLM metrics are empty; only memory/routing evaluated.")
    print(bar)


def main() -> int:
    cases = load_cases(CASES_PATH)
    print(f"Loaded {len(cases)} evaluation cases from {CASES_PATH}")
    print(f"USE_LIVE_LLM = {USE_LIVE_LLM}")

    has_ab_flags = hasattr(app_module, "USE_QUERY_REWRITE") and hasattr(app_module, "USE_RERANK")
    run_ab = USE_LIVE_LLM and has_ab_flags

    if USE_LIVE_LLM:
        print("Building RAG system (one-time initialization)...")
        build_rag_system()
        print("RAG system ready.")

    if run_ab:
        print("A/B flags detected in app — running 4-mode comparison...")
        saved_rw = getattr(app_module, "USE_QUERY_REWRITE", True)
        saved_rr = getattr(app_module, "USE_RERANK", True)
        mode_runs = []
        try:
            for mode_name, use_rewrite, use_rerank in AB_MODES:
                mode_runs.append(run_mode(mode_name, use_rewrite, use_rerank, cases))
        finally:
            _set_ab_flags(saved_rw, saved_rr)

        print_ab_comparison(mode_runs)
        print_interpretation(mode_runs)

        full_run = next((r for r in mode_runs if r["mode"] == "full"), mode_runs[-1])
        print_report(full_run["summary"], full_run["results"])

        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump({"summary": full_run["summary"], "results": full_run["results"]},
                      f, ensure_ascii=False, indent=2)
        with open(AB_RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump({"modes": mode_runs}, f, ensure_ascii=False, indent=2)
        print(f"Per-case detail (full mode): {RESULTS_PATH}")
        print(f"A/B comparison artifact:     {AB_RESULTS_PATH}")
    else:
        if not USE_LIVE_LLM:
            print("USE_LIVE_LLM=False — running offline (memory/routing only, no LLM calls)...")
        elif not has_ab_flags:
            print("No A/B flags in app — running single-mode evaluation...")

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
