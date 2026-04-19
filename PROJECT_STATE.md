# Project State

## System status

**Phase 0-6.5:** Core capabilities implemented.

**Phase 6.6-prep:**
- Evaluation comparability enabled
- Retrieval A/B modes stabilized (baseline / rewrite_only / rerank_only / full)
- Decision scoring improved (action-level keyword overlap)

## What is validated

- Mode switching actually changes the code path (rewrite and rerank divergence verified)
- Rerank changes document ordering (not just a surface flag)
- Budget parity across all 4 modes (same `top_n` cap)
- Per-case metadata includes `mode` (self-contained result records)
- Evaluation runs end-to-end (offline and live paths)

## What is partial / MVP

- Retrieval metrics are limited (recall-heavy; no MRR or nDCG)
- Dataset size is still small (~24 cases)
- Trust scoring exists but is not deeply validated against outcomes
- Memory usage is not yet fully benchmarked
- Live LLM evaluation is not fully characterized (mocked smoke tests only so far)

## Known gaps

- No cross-encoder rerank (token-overlap heuristic only)
- No deep retrieval metrics (MRR / nDCG)
- No structured output validation layer (schema is enforced, content is not audited)
- No formal memory retrieval benchmarking
- Action matching uses keyword overlap, not semantic similarity

## Next direction

- Strengthen evaluation rigor (larger dataset, per-stratum breakdown)
- Improve retrieval quality measurement (beyond hit-rate)
- Improve decision-grounding reliability (trust signal calibration)
- Prepare integration contract with AI MES Copilot
