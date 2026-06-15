# Project State

## System status

**Phase 0-6.5:** Core capabilities implemented.

**Phase 6.6-prep:**
- Evaluation comparability enabled
- Retrieval A/B modes stabilized (baseline / rewrite_only / rerank_only / full)
- Decision scoring improved (action-level keyword overlap)

**Phase 6.6 (A/B closeout):** ✅ Done. 4-mode A/B artifact committed in `eval/eval_ab_results.json` against the 40-case benchmark.

**Phase 6.7:** ✅ Done. `MRR` and `nDCG@3` added to `eval/run_eval.py` summary metrics.

**Phase 6.8:** ✅ Done. Benchmark expanded from 10 → 40 cases; 37 carry `expected_sources` labels.

**G2 (metadata filter):** ✅ Implemented on main. `doc_type` tagging + query-class filter in `app.py`.

**G4 (eval regression gate):** ✅ Implemented on main; baseline gate PASS. `eval/run_baseline_check.py` + `eval/baseline_metrics.json`.

**Course-driven gap items:** G2 (metadata filter) and G4 (eval regression gate) ✅ implemented on main (see above); G3 (LLM rewrite) and G1 (LoRA fine-tune) remain planned. Per-item detail in `AI_ROADMAP.md` → "Course-driven gap items". Execution order in `NEXT_STEPS.md`.

**Enterprise readiness track (planned):** ENT-1 (Docker), ENT-2 (API auth + rate limiting), ENT-3 (`/health` + `/metrics`). Per-item detail in `AI_ROADMAP.md` → "Enterprise readiness track".

**Resume-ready Polish Track (Portfolio Packaging) — Completed (Portfolio Packaging):** Shipped packaging-only items: LICENSE (MIT), `baseline_metrics.json`, A/B chart (`docs/images/ab_results.png`), README hero figure (`docs/images/ab_hero.png`) + Highlights, README final polish. **Not a research phase**; does not replace G3 / G1 / Phase 7B / FastAPI work. Detail in `AI_ROADMAP.md` → "Resume-ready Polish Track (Portfolio Packaging)".

**Decision-Layer Track:** Phase 7 strict prompt = HOLD (audit branch preserved); Phase 7B Action Canonicalization = planned / design-ready (`docs/architecture/ADR_007_action_canonicalization.md`). Phase 7 FastAPI serving remains future work.

## What is validated

- Mode switching actually changes the code path (rewrite and rerank divergence verified)
- Rerank changes document ordering (not just a surface flag)
- Budget parity across all 4 modes (same `top_n` cap)
- Per-case metadata includes `mode` (self-contained result records)
- Evaluation runs end-to-end (offline and live paths)

## What is partial / MVP

- Retrieval metrics now include MRR and nDCG@3 (Phase 6.7); per-stratum and confidence-interval breakdowns still pending
- Dataset is 40 cases (37 graded; Phase 6.8); 100+ target with inter-rater on 20% sample tracked as backlog #4
- Trust scoring exists but is not deeply validated against outcomes
- Memory usage is not yet fully benchmarked
- Live LLM evaluation is not fully characterized (mocked smoke tests only so far)

## Known gaps

- No cross-encoder rerank (token-overlap heuristic only) — tracked as backlog #3
- Deep retrieval metrics (MRR / nDCG@3) added in Phase 6.7; per-stratum / per-class breakdown still pending
- No structured output validation layer (schema is enforced, content is not audited)
- No formal memory retrieval benchmarking
- Action matching uses keyword overlap, not semantic similarity
- No container packaging or production serving surface — tracked as ENT-1 / Phase 7 / ENT-2 / ENT-3

## Next direction

- Strengthen evaluation rigor (larger dataset, per-stratum breakdown)
- Improve retrieval quality measurement (beyond hit-rate)
- Improve decision-grounding reliability (trust signal calibration)
- Prepare integration contract with AI MES Copilot
- See `NEXT_STEPS.md` → "Current execution sequence (post Phase 6.6 closeout)" for the dependency-aware IMMEDIATE → LONG-TERM ordering.
