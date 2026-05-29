# ADR-007: Action Canonicalization Layer

- **Status:** Accepted (design phase; implementation deferred to a separate branch)
- **Date:** 2026-05-11
- **Supersedes:** N/A
- **Related branches:** `phase7-prompt-hardening` (held experiment, see below)
- **Roadmap:** `AI_ROADMAP.md` → "Decision-Layer Track (Phase 7 / Phase 7B)"

## Context

After Phase 6.8 (40-case benchmark expansion) and G2 (`doc_type` metadata filter) merged to `main`, retrieval quality reached a clear plateau under all four A/B modes:

| metric | full mode |
|---|---|
| `retrieval_hit_rate` | 0.829 |
| `top_k_hit_rate` | 0.829 |
| `avg_mrr` | 0.800 |
| `avg_ndcg_at_k` | 0.763 |
| `avg_decision_match` | **0.656** |

`avg_decision_match` was the lowest metric, and it stayed flat under retrieval-side levers (chunking, embedding, rerank, query rewrite, metadata filter — none of those moved it materially). `decision_match = 0.5·type_score + 0.5·action_score`, and with `anomaly_type_accuracy` ≈ 0.73, the implied `action_score` ≈ 0.54 was the dominant drag.

`_action_match_score` in `eval/run_eval.py` is purely lexical: for each `expected_action`, it tokenizes the string and counts a match when ≥50% of expected tokens appear anywhere in the concatenated predicted-action pool. The only lever that can lift this score is **alignment of surface vocabulary between predicted and expected action strings**.

Phase 7 (Evidence-bound Decision Reasoning, Option A from the architect-review thread) was proposed as an additive LLM-side prompt + schema change, on the hypothesis that forcing citation of retrieved chunks would drag predicted action wording toward verbatim SOP language and lift `action_score` as a side effect.

## Experiment

Two prompt variants tested behind `USE_DECISION_REASONING` flag (default `False`); flag-gated and reversible by design. Schema change (`evidence_to_action: Optional[List[EvidenceToAction]]`) was additive — backward compatible.

| Variant | Description | `decision_match` Δ |
|---|---|---|
| Gentle directive | Ask for grounding, allow `supporting_source:"none"` stubs for ungrounded actions. | 0.656 → 0.660 (+0.004; indistinguishable from 40-case noise) |
| Strict directive (R1–R4 + BAD/GOOD few-shot) | Every action grounded; verbatim SOP wording preferred; ungrounded actions **omitted** instead of stubbed; source excerpt quoted (10–40 chars). | 0.656 → **0.646 (−0.010)** |

Retrieval guardrails — `retrieval_hit_rate`, `top_k_hit_rate`, `avg_mrr`, `avg_ndcg_at_k` — were all flat (0.829 / 0.829 / 0.800 / 0.763) under both variants, confirming the prompt change did not bleed into retrieval.

## Result

The hypothesis that prompt strictness alone can lift `action_score` is **not supported** by the 40-case data. The strict variant slightly regressed for three reasons:

1. **Over-pruning of grounded actions.** Strict R3 ("omit if no support") removed actions that, under softer wording, would have keyword-matched `expected_actions` even without verbatim SOP support.
2. **Verbatim mandate did not align tokens.** `expected_actions` in `eval_cases.json` are themselves *paraphrased* SOP — not always verbatim from `rag_data/`. Forcing the LLM to copy from `rag_data/` chunks sometimes *increased* lexical drift relative to the benchmark labels rather than reducing it.
3. **Scorer is purely lexical.** Semantically equivalent phrases that share no surface tokens score zero. The scorer cannot reward `"停止機台"` as a match for expected `"Hold equipment"` even though both refer to the same SOP step.

## Decision

Do **not** continue increasing prompt strictness as the primary lever for `decision_match`. The remaining gap is dominated by **semantic equivalence that the scorer cannot see**, not by reasoning quality or grounding discipline.

Introduce an **Action Canonicalization Layer** (Phase 7B) that normalizes both predicted and expected action phrases to a small canonical vocabulary **before** scoring. Example mapping (illustrative — full vocabulary to be drafted in implementation):

| surface variants | canonical form |
|---|---|
| `"停止機台"`, `"Hold 設備"`, `"暫停 production"`, `"tool hold"`, `"設備暫停"` | `Hold equipment` |
| `"通知 on-call"`, `"On-Call Engineer 接手"`, `"call duty engineer"` | `Notify on-call engineer` |
| `"49 點 map"`, `"49-point map"`, `"全 wafer 49 點"`, `"49pt"` | `Collect 49-point map` |
| `"3-sigma 超標"`, `"3σ out of spec"`, `"3sigma OOC"` | `3-sigma out of control` |
| ... | ... |

The canonicalizer runs **inside the scorer** (eval-only), not in the retrieval or LLM path. This explicitly separates two concerns:

- **Semantic correctness** — the scorer's responsibility. Should reward any phrasing of the right action.
- **Lexical token overlap** — a free-text property that should not gate semantic correctness.

## Consequences

### Positive

- Action equivalence becomes an **explicit, auditable vocabulary** (a reviewable file) instead of an implicit lexical accident in `_action_match_score`.
- Avoids over-optimizing the prompt for scorer wording (a textbook Goodhart's-law risk that Phase 7 strict directly exhibited).
- Existing `eval_cases.json` `expected_actions` labels stay unchanged — the canonicalizer is additive on top.
- Reusable methodology: every future retrieval / prompt experiment gets scored against a stable semantic target rather than a moving lexical one.
- Decouples LLM output style from scoring rigor — useful when comparing future model upgrades whose natural phrasing differs from the current one.

### Negative / risks

- The canonical vocabulary is itself a hand-curated artifact and inherits Goodhart risk one level removed — someone has to write the mapping, and it can be over-tuned to the 40-case benchmark.
- An over-aggressive canonicalizer could mask real reasoning errors by collapsing genuinely distinct actions to the same canonical form. Mitigation: keep canonical forms coarse (one per SOP step) and review any collapse that yields > +0.04 lift for plausibility.
- First-pass canonicalizer will be heuristic (keyword / regex). A more principled approach — embedding-based clustering, or LLM-as-judge action equivalence — is deferred to a later iteration.
- Adds an eval-time dependency (the vocabulary file must exist and be loadable) that the raw scorer does not have. Mitigation: flag-gate the canonicalizer so raw scoring still works for reproducibility.

### Out of scope for Phase 7B implementation

- No change to `app.py`, retrieval, rerank, query rewrite, routing, memory, trust scoring, prompts, or `MESAnalysisOutput` schema.
- No change to `eval_cases.json` content (`expected_actions` labels stand).
- No change to LLM provider, chain construction, or `evidence_to_action` field (which remains on main behind the default-False flag from Phase 7).
- No re-run of the full 40-case LLM eval for the first canonicalizer pass — apply to existing held artifacts.

### In scope for Phase 7B implementation

- New file `eval/action_vocabulary.json` (or similar) — reviewable plain-data file.
- New file `eval/action_canonicalization.py` (or similar) — the normalizer.
- Wire normalizer into `_action_match_score` behind a flag (default OFF, so baseline numbers stay reproducible).
- A/B the scorer on the held-out reasoning-OFF artifact: raw vs canonicalized.
- Document the vocabulary curation process and Goodhart guardrails in this ADR's follow-up section once implemented.

## Acceptance criteria for Phase 7B

- `action_score` lift **≥ +0.020** on the OFF artifact under canonicalized scoring (i.e., enough to clear the G4 ±0.020 noise threshold).
- Canonical vocabulary is reviewable as a plain text / JSON file — no opaque ML model in the first pass.
- Raw scorer still works behind the same flag, so existing `eval_ab_results.json` numbers remain reproducible.
- G4 baseline regression gate continues to pass under both raw and canonicalized scoring.
- Each canonical collapse that contributes > +0.005 to `action_score` is annotated with its surface variants in the vocabulary file for review.

## Failure mode

If canonicalized `action_score` lifts < +0.020, the bottleneck is **not** lexical mismatch. In that case the hypothesis is wrong and the next escalation is one of:

- LLM-as-judge action-equivalence scoring (more expensive, less reproducible).
- Embedding-based action matching (introduces an ML dependency in eval).
- `expected_actions` label review — the labels themselves may be the limiting factor, not the scorer or the LLM.

## Status timeline

- **2026-05-11**: ADR accepted. Phase 7B in design phase. Implementation branch not yet created. `phase7-prompt-hardening` branch preserved as audit trail for the held experiment.
- **Next checkpoint**: create implementation branch from `main` named `feat/phase7b-action-canonicalization` once vocabulary skeleton is drafted in this ADR and reviewed.
