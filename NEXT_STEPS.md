# Next Steps

## Active focus (post G2 + G4 merge, Phase 7 evaluated)

Phase 7 strict evidence-bound reasoning prompt was tested on branch `phase7-prompt-hardening`. G4 gate PASS, but `decision_match` 0.656 → 0.646 (−0.010). Retrieval metrics flat. **Not a production improvement.** See `AI_ROADMAP.md` → "Decision-Layer Track (Phase 7 / Phase 7B)" and `docs/architecture/ADR_007_action_canonicalization.md`.

### Immediate actions
1. **Do not merge `phase7-prompt-hardening` as-is.** Strict prompt regressed `decision_match` and is HOLD. The branch is **not** a production candidate.
2. **Preserve branch `phase7-prompt-hardening`** as an experiment / audit trail. Do not delete locally or on remote.
3. **Start documentation + design for Phase 7B — Action Canonicalization Layer.** Methodology change inside the scorer, not a retrieval / prompt / schema change. Design lives in `docs/architecture/ADR_007_action_canonicalization.md`.
4. **Only after this doc sync lands**, decide whether to create a new implementation branch (recommended name: `feat/phase7b-action-canonicalization`, branched from `main`).

### Why this order
- The held experiment is a real result worth documenting; deleting the branch or rewriting history would lose the evidence that prompt strictness is the wrong lever.
- Phase 7B is an eval-methodology change — designing the canonical vocabulary on paper is cheap and reviewable before any code runs.
- Branching for 7B from `main` (not from `phase7-prompt-hardening`) keeps 7B clean of the held strict-prompt code.

---

## Current execution sequence (post Phase 6.6 closeout)

Sequenced by **dependency**, not by recency. Per-item detail and acceptance criteria live in `AI_ROADMAP.md` ("Course-driven gap items", "Enterprise readiness track", "Near-term engineering backlog").

### IMMEDIATE — finish foundation
1. **Phase 6.6 closeout** — ✅ done. A/B artifact committed (40 cases × 4 modes) in `eval/eval_ab_results.json`.
2. **G4 — eval baseline regression gate** — ✅ done; implemented on main, baseline gate PASS. `eval/run_baseline_check.py` + `eval/baseline_metrics.json`. Turns the Phase 6.6 baseline into a contract.
3. **G2 — metadata filter** — ✅ done; implemented on main. `doc_type` tag on chunks + query-class filter via `classify_query()`. Root-cause fix for ~5 misclassified eval cases.
4. **Doc reconciliation** — sync stale facts in `PROJECT_STATE.md` and this file. ← only remaining IMMEDIATE item (this PR).

**Next active work (dependency order):** (a) Backlog #4 — expand benchmark to 100+ cases; (b) Phase 7B Action Canonicalization (zero-dependency, design-ready); (c) Phase 7 FastAPI serving, later.

### SHORT-TERM — measurement floor before any tuning
5. **Backlog #4** — expand `eval/eval_cases.json` to 100+ cases with `expected_sources` everywhere; inter-rater on a 20% sample (target agreement ≥ 0.8).
6. **Backlog #2** — embedding model benchmark (`bge-m3` / `gte-multilingual-base` / E5 variants), graded under the G4 gate.
7. **Backlog #1** — chunking strategy A/B (3–4 configurations), graded under the G4 gate.

### MID-TERM — tuning given a real measurement floor
8. **Backlog #3** — cross-encoder rerank (`bge-reranker-v2-m3`), consumes the G2-filtered candidate set.
9. **G3** — LLM-based query rewrite, gated A/B against the heuristic on the 100+ benchmark. Ships only if delta beats noise.
10. **G1** — LoRA fine-tune the embedding model selected by backlog #2. Adapter ships only if it beats the base on G4 gate.

### LONG-TERM — serving / enterprise
11. **ENT-1 — Docker** — wrap current Gradio; updates in lockstep with Phase 7. Parallel-track, no upstream blocker.
12. **Phase 7 — FastAPI** — replace Gradio as the serving surface.
13. **ENT-2 — API auth + rate limiting**, **ENT-3 — `/health` + `/metrics`** — both post-Phase 7.
14. **Phase 8 — ingestion**, **Phase 9 — reliability / circuit breaker**, **Backlog #5 — multimodal RAG**.

### Why this order (the four "before" rules)
- Phase 6.6 closeout **before** any retrieval/embedding tuning — without a committed baseline, every later "improved X by Y" claim is unfalsifiable.
- G4 **before** short-term A/B work — turns the baseline into a gate so parallel changes don't lose attribution.
- G2 **before** backlog #3 cross-encoder — filter then rank; rerank on unfiltered candidates conflates two jobs.
- Backlog #4 **before** G3 / G1 — 40 cases cannot detect realistic 3–5 point tuning deltas above noise.
- Backlog #2 **before** G1 — fine-tuning the wrong base model is wasted GPU.

---

## Resume-ready Polish Track (Portfolio Packaging)

Parallel **packaging** track — not part of the dependency-ordered engineering sequence above and **not a new research phase**. Purpose is cold email / résumé / professor outreach packaging of work already on `main`. Full item list and boundaries live in `AI_ROADMAP.md` → "Resume-ready Polish Track (Portfolio Packaging)".

Planned short-term items (each a separate follow-up PR; none touch runtime / schema / routing / eval scoring logic):
1. LICENSE (MIT)
2. `baseline_metrics.json` — G4 / portfolio reproducibility snapshot (supports G4, does not change it)
3. `docs/images/ab_results.png` — static A/B chart from `eval/eval_ab_results.json`
4. README metrics table / portfolio framing polish
5. Architecture diagram refresh (only if low-effort)

Does **not** replace or reprioritize G2, G4 hardening, Phase 7B, or FastAPI work.

---

## Current focus (post Phase 6.6-prep) — historical reference

Preserved verbatim from before Phase 6.6 closeout. Items already shipped are annotated; remaining items are subsumed by the IMMEDIATE / SHORT-TERM blocks above.

- Formal A/B measurement (baseline vs rewrite vs rerank vs full) — ✅ done in Phase 6.6
- Retrieval quality metrics expansion (beyond recall) — ✅ MRR + nDCG@3 added in Phase 6.7
- Memory-grounded reasoning validation — still open; not yet in execution sequence
- Trust scoring signal validation — still open; not yet in execution sequence
- Dataset expansion (`eval/eval_cases.json`) — partial: 10 → 40 in Phase 6.8; 100+ target tracked as backlog #4 above

## Short-term goals (interview readiness)

- Ensure evaluation outputs are interpretable
- Ensure metrics reflect real decision quality (not just type-matching)
- Keep system explainable (not just accurate)
