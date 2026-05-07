"""
Phase G4: Eval baseline regression gate.

Compares the current eval run's summary metrics against the committed Phase 6.6
A/B baseline (eval/eval_ab_results.json) and exits non-zero if any tracked
metric regresses beyond a per-metric threshold.

Usage:
  python eval/run_baseline_check.py
  python eval/run_baseline_check.py --baseline-mode full --threshold 0.02
  python eval/run_baseline_check.py --current eval/eval_results.json

Inputs:
  --baseline       Path to A/B artifact   (default: eval/eval_ab_results.json)
  --baseline-mode  Mode key inside it     (default: full)
  --current        Path to current run    (default: eval/eval_results.json)
  --threshold      Per-metric tolerance   (default: 0.02)

Exit code:
  0 — PASS (no tracked metric regressed beyond threshold)
  1 — FAIL (one or more regressions; see report)
"""

import argparse
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_BASELINE_PATH = EVAL_DIR / "eval_ab_results.json"
DEFAULT_CURRENT_PATH = EVAL_DIR / "eval_results.json"
DEFAULT_BASELINE_MODE = "full"
DEFAULT_THRESHOLD = 0.02

TRACKED_METRICS = [
    "retrieval_hit_rate",
    "top_k_hit_rate",
    "avg_mrr",
    "avg_ndcg_at_k",
    "avg_decision_match",
]


def _load_baseline_summary(path: Path, mode_name: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    modes = data.get("modes", [])
    for m in modes:
        if m.get("mode") == mode_name:
            return m.get("summary", {})
    available = [m.get("mode") for m in modes]
    raise SystemExit(
        f"Baseline mode '{mode_name}' not found in {path}. Available modes: {available}"
    )


def _load_current_summary(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "summary" in data:
        return data["summary"]
    if "modes" in data:
        raise SystemExit(
            f"Current file {path} looks like an A/B artifact (has 'modes'). "
            f"Pass a single-mode results file via --current."
        )
    raise SystemExit(f"Could not find 'summary' in {path}")


def compare(baseline: dict, current: dict, threshold: float):
    regressions = []
    deltas = []
    for key in TRACKED_METRICS:
        b = baseline.get(key)
        c = current.get(key)
        if b is None or c is None:
            deltas.append((key, b, c, None))
            continue
        delta = c - b
        deltas.append((key, b, c, delta))
        if delta < -threshold:
            regressions.append((key, b, c, delta))
    return regressions, deltas


def _fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def print_report(deltas, regressions, threshold, baseline_mode, baseline_path, current_path):
    bar = "=" * 72
    print(bar)
    print("EVAL BASELINE REGRESSION CHECK")
    print(bar)
    print(f"  baseline:  {baseline_path}  (mode: {baseline_mode})")
    print(f"  current:   {current_path}")
    print(f"  threshold: -{threshold:.3f}  (FAIL if current < baseline by more)")
    print("-" * 72)
    print(f"  {'METRIC':<24}{'BASELINE':<12}{'CURRENT':<12}{'DELTA':<12}STATUS")
    for name, b, c, d in deltas:
        if d is None:
            status = "skip"
            d_str = "-"
        elif d < -threshold:
            status = "FAIL"
            d_str = f"{d:+.3f}"
        else:
            status = "ok"
            d_str = f"{d:+.3f}"
        print(f"  {name:<24}{_fmt(b):<12}{_fmt(c):<12}{d_str:<12}{status}")
    print(bar)
    if regressions:
        print(f"FAIL:{len(regressions)} metric(s) regressed beyond -{threshold:.3f}:")
        for name, b, c, d in regressions:
            print(f"  - {name}: {b:.3f} -> {c:.3f} ({d:+.3f})")
    else:
        print("PASS: no tracked metric regressed beyond threshold.")
    print(bar)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Eval baseline regression gate (Phase G4).",
    )
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE_PATH),
                    help="Path to baseline A/B artifact (default: eval/eval_ab_results.json)")
    ap.add_argument("--baseline-mode", default=DEFAULT_BASELINE_MODE,
                    help="Mode name inside baseline artifact (default: full)")
    ap.add_argument("--current", default=str(DEFAULT_CURRENT_PATH),
                    help="Path to current run summary (default: eval/eval_results.json)")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help="Per-metric regression tolerance (default: 0.02)")
    args = ap.parse_args()

    baseline_path = Path(args.baseline)
    current_path = Path(args.current)

    baseline = _load_baseline_summary(baseline_path, args.baseline_mode)
    current = _load_current_summary(current_path)

    regressions, deltas = compare(baseline, current, args.threshold)
    print_report(deltas, regressions, args.threshold, args.baseline_mode,
                 baseline_path, current_path)
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
