# Next Steps

## Current execution sequence (post Phase 6.6 closeout)

Sequenced by **dependency**, not by recency. Per-item detail and acceptance criteria live in `AI_ROADMAP.md` ("Course-driven gap items", "Enterprise readiness track", "Near-term engineering backlog").

### IMMEDIATE — finish foundation
1. **Phase 6.6 closeout** — ✅ done. A/B artifact committed (40 cases × 4 modes) in `eval/eval_ab_results.json`.
2. **G4 — eval baseline regression gate** — `eval/run_baseline_check.py` + `eval/baseline_metrics.json`. Turns the Phase 6.6 baseline into a contract.
3. **G2 — metadata filter** — `doc_type` tag on chunks + Chroma `where=` filter via `classify_query()`. Root-cause fix for ~5 misclassified eval cases. No upstream blocker.
4. **Doc reconciliation** — sync stale facts in `PROJECT_STATE.md` and this file.

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
