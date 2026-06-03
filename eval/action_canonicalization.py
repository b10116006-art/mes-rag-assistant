"""Phase 7B: Action Canonicalization Layer (eval-side only).

Normalizes both predicted and expected action phrases to a small canonical
vocabulary before token-overlap matching in eval/run_eval.py's
_action_match_score. Eval-side only — no runtime impact, no change to the
MESAnalysisOutput schema or the Gradio path.

Design (first pass, intentionally simple):
  - Plain JSON vocabulary (eval/action_vocabulary.json), reviewable as text.
  - Case-insensitive substring replacement.
  - Longer variants are matched before shorter ones so "On-Call Engineer"
    canonicalizes before bare "On-Call".
  - Each known surface variant collapses to a single snake_case canonical
    token (e.g. "hold_equipment") that the token-overlap scorer treats as
    one matchable unit.

ADR: docs/architecture/ADR_007_action_canonicalization.md
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

VOCAB_PATH = Path(__file__).resolve().parent / "action_vocabulary.json"

_compiled: Optional[List[Tuple[re.Pattern, str]]] = None


def load_vocabulary(path: Path = VOCAB_PATH) -> List[Tuple[re.Pattern, str]]:
    """Read the vocabulary JSON and compile its variants to (regex, canonical)
    pairs, globally sorted by variant length descending so longer phrases
    win over shorter prefixes contained within them."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    pairs: List[Tuple[str, str]] = []
    for entry in data.get("aliases", []):
        canonical = entry["canonical"]
        for variant in entry.get("variants", []):
            if variant:
                pairs.append((variant, canonical))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    compiled: List[Tuple[re.Pattern, str]] = []
    for variant, canonical in pairs:
        # Allow flexible internal whitespace between the variant's tokens
        # so "通知 on-call" still matches "通知  on-call" etc.
        body = r"\s+".join(re.escape(tok) for tok in variant.split())
        compiled.append((re.compile(body, flags=re.IGNORECASE), canonical))
    return compiled


def _get_compiled() -> List[Tuple[re.Pattern, str]]:
    global _compiled
    if _compiled is None:
        _compiled = load_vocabulary()
    return _compiled


def reset_cache() -> None:
    """Drop the compiled-vocabulary cache. For tests/smoke that reload
    an updated JSON in-process."""
    global _compiled
    _compiled = None


def canonicalize_phrase(text: str) -> str:
    """Replace every known surface variant in *text* with its canonical
    token. Unknown phrases pass through unchanged. Case-insensitive."""
    if not text:
        return text
    out = text
    for pattern, canonical in _get_compiled():
        out = pattern.sub(canonical, out)
    return out


def canonicalize_actions(actions: Iterable[str]) -> List[str]:
    """Apply canonicalize_phrase to each item in *actions*."""
    return [canonicalize_phrase(a) for a in actions]
