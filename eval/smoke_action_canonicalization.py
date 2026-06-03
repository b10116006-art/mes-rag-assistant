"""Smoke check for eval/action_canonicalization.py.

Run:
  python eval/smoke_action_canonicalization.py

Exits 0 on PASS (all assertions hold), 1 on FAIL.

Asserts:
  1. Known surface variants for the same SOP step canonicalize to the
     same string (case-insensitive).
  2. Distinct SOP steps do NOT collapse to the same canonical form.
  3. Unknown phrases pass through unchanged.
  4. A reconstructed token-overlap action_score is strictly higher when
     canonicalization is applied, on a small constructed paraphrase pair
     that fails under raw lexical scoring.

No live LLM, no network, no file writes. Only reads
eval/action_vocabulary.json via action_canonicalization.load_vocabulary.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make the eval/ directory importable when this file is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from action_canonicalization import (  # noqa: E402
    canonicalize_actions,
    canonicalize_phrase,
)


def _action_match_score(expected, predicted):
    """Local replica of eval/run_eval.py::_action_match_score so the smoke
    runs without importing the full app (which would pull in LangChain)."""
    if not expected:
        return None
    if not predicted:
        return 0.0
    pool = " ".join(predicted).lower()
    matched = 0
    for ea in expected:
        toks = set(ea.lower().split()) - {""}
        if not toks:
            continue
        if sum(1 for t in toks if t in pool) / len(toks) >= 0.5:
            matched += 1
    return round(matched / len(expected), 3)


def main() -> int:
    failures: list[str] = []

    # 1. Variant equivalence — each pair must canonicalize identically.
    equivalences = [
        ("Hold 設備", "停止機台"),
        ("Hold 設備", "tool hold"),
        ("通知 process engineer", "聯絡 process engineer"),
        ("通知 on-call engineer", "On-Call Engineer 接手"),
        ("執行 nf3 腔體清潔", "NF3 clean"),
        ("檢查 shower head", "showerhead 檢查"),
        ("確認 mfc 是否異常", "MFC 檢查"),
        ("3-sigma 超標", "3sigma OOC"),
    ]
    for a, b in equivalences:
        ca = canonicalize_phrase(a).lower()
        cb = canonicalize_phrase(b).lower()
        if ca != cb:
            failures.append(
                f"variants differ: {a!r} -> {ca!r}  vs  {b!r} -> {cb!r}"
            )

    # 2. Distinct SOP steps must NOT collide.
    distincts = [
        ("Hold 設備", "通知 process engineer"),
        ("檢查 shower head", "檢查 mfc"),
        ("nf3 chamber clean", "leak check"),
    ]
    for a, b in distincts:
        ca = canonicalize_phrase(a).lower()
        cb = canonicalize_phrase(b).lower()
        if ca == cb:
            failures.append(f"distinct steps collapsed: {a!r} and {b!r} -> {ca!r}")

    # 3. Unknown phrases pass through unchanged.
    unknown = "請執行不存在的步驟 XYZ"
    if canonicalize_phrase(unknown) != unknown:
        failures.append(
            f"unknown phrase mutated: {unknown!r} -> {canonicalize_phrase(unknown)!r}"
        )

    # 4. Action-score lift on a constructed paraphrase pair.
    expected = ["Hold 設備", "通知 on-call engineer"]
    predicted_raw = ["停止機台", "On-Call Engineer 接手"]
    raw_score = _action_match_score(expected, predicted_raw)
    canon_score = _action_match_score(
        canonicalize_actions(expected),
        canonicalize_actions(predicted_raw),
    )
    if canon_score is None or raw_score is None or canon_score <= raw_score:
        failures.append(
            f"canonicalized score did not exceed raw: raw={raw_score}, canon={canon_score}"
        )

    bar = "=" * 60
    print(bar)
    print("Phase 7B Action Canonicalization — smoke check")
    print(bar)
    print(f"  equivalence pairs tested: {len(equivalences)}")
    print(f"  distinct-pair tests:      {len(distincts)}")
    print(f"  unknown-passthrough test: 1")
    print(f"  paraphrase lift test:     raw={raw_score}  canon={canon_score}")
    print("-" * 60)
    if failures:
        print(f"FAIL ({len(failures)} issue(s)):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
