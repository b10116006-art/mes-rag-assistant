# Changelog

## 2026-04-16 — Phase 6.7: Benchmark Expansion & Filename Alignment

- Expanded `eval/eval_cases.json` from 10 → 40 labeled cases (15 anomaly, 15 sop_doc, 10 general)
- All `expected_sources` aligned to the 4 real filenames currently in `rag_data/` (`01_異常類型定義.md`, `02_SOP_異常處置流程.md`, `03_AI_Copilot判斷邏輯.md`, `04_設備常見問題集.md`). No phantom filenames.
- Every case includes all required fields: `id`, `type`, `tag`, `query`, `expected_sources`, `expected_anomaly_type`, `expected_memory_used`, `expected_route_used`
- Updated `AI_ROADMAP.md`, `CHANGELOG.md`, `README.md` to document Phase 6.7 completion, honest evaluation limitations, and the next-step plan
- **Not included in this phase:** live API evaluation runs, architecture refactors, new dependencies, UI changes, or production accuracy claims. All numbers produced so far are framework smoke-test results, not final model performance.

## 2026-04-15 — Docs: Phase 6.6 evaluation limitations documented

- `AI_ROADMAP.md` — added an explicit "Current limitations" subsection under Phase 6.6 covering dataset size, hand-labeled `expected_sources`, the regression-detection orientation of the harness, and the fact that mocked smoke runs do not produce citable accuracy numbers
- `AI_ROADMAP.md` — added a "Next step (recommended)" subsection making the 100+ case benchmark expansion and a real-provider A/B run a prerequisite for further retrieval-layer work
- `README.md` — added a short "Evaluation status" note so external readers see the constraints before any numbers
- No runtime code changes in this entry (docs only)

## 2026-04-14 — Phase 6.5: Retrieval Evaluation Layer

- Extended `eval/eval_cases.json` with an optional `expected_sources` field per case (additive; pre-existing fields unchanged). Populated for the 7 cases where a clear doc mapping exists; left as `[]` for the 3 general-knowledge cases
- Extended `eval/run_eval.py` to read the Phase 6 retrieval debug fields (`retrieved_count`, `reranked_count`, `top_sources`) from the structured analysis output and compute three per-case retrieval metrics when `expected_sources` is provided:
  - `retrieval_hit` — any expected source appears in `top_sources`
  - `top_k_hit` — same as `retrieval_hit` since `top_sources` is already capped at the app-side top-k window
  - `source_overlap` — integer count of expected ∩ actual sources
- Added four summary-level aggregates: `retrieval_graded_cases`, `retrieval_hit_rate`, `top_k_hit_rate`, `avg_source_overlap`, plus `avg_retrieved_count` / `avg_reranked_count` across the full run
- Extended the per-case console table with `retr` and `ovlp` columns (`-` for ungraded cases)
- `eval/eval_results.json` schema gains the new per-case fields automatically via the existing dict serialization
- No changes to `app.py`, chain logic, retrieval, memory, routing, trust layer, or UI

## 2026-04-14 — Phase 6: Retrieval Rerank Layer

- New helper `rerank_docs(query, docs, top_n=6)` — lightweight token-overlap rerank. No new dependency; reuses the existing `_tokenize()` helper from the memory layer
- New helper `make_rerank_retriever(base_retriever, top_n, top_sources_k)` — wraps a base retriever as a `RunnableLambda` that runs vector retrieval, reranks, and writes retrieval debug signals into a module-level `_last_retrieval_debug` dict
- All 4 chain wirings in `build_rag_system` (gemini chat, gemini analysis, openai chat, openai analysis) now pipe through `make_rerank_retriever(...)` before `format_docs`. No change to retriever construction, vector store, or embeddings
- Added `RunnableLambda` to the existing `langchain_core.runnables` import (additive)
- Added three retrieval debug fields to every structured analysis output:
  - `retrieved_count: int` — raw docs returned by the vector/multi-query retriever
  - `reranked_count: int` — docs kept after token-overlap rerank
  - `top_sources: list[str]` — up to 3 unique source filenames of the top-reranked docs
- Chat mode is intentionally untouched in this phase — the rerank layer still runs (so retrieval quality improves for chat), but the chat header already carries memory/route/rewrite/trust lines and adding three more was rejected on minimal-diff grounds. Chat debug visibility deferred.
- No changes to `MESAnalysisOutput` schema, memory logic, routing logic, query rewrite, trust layer, evaluation script, or UI

## 2026-04-14 — Phase 5: Decision Trust Layer

- New helper `compute_trust_score(matched_case_ids, route_used, confidence, evidence_sources, provider_used)` — pure heuristic, no LLM, no new deps
- Scoring: starts from 0.5 neutral baseline, applies additive deltas, clamps to [0, 1]:
  - `+0.4` if memory matched (`matched_case_ids` non-empty)
  - `+0.2` if `route_used == "rag"`
  - `-0.2` if `route_used == "llm"`
  - `-0.2` if `"fallback" in provider_used`
  - `+0.2` if `evidence_sources` non-empty
- Adds three additive fields to every structured analysis output:
  - `trust_score: float` (2-decimal, 0–1)
  - `trust_level: str` — `HIGH` (≥0.75) / `MEDIUM` (≥0.5) / `LOW` (<0.5)
  - `trust_reason: str` — short explanation listing which deltas fired
- **Analysis mode:** injected via `output.update(compute_trust_score(...))` immediately after `compute_trust_signals` in all 5 analysis branches
- **Chat mode:** nested `_trust_lines(provider_label)` closure called per return branch; emits `【trust_score: ...】` + `【trust_level: ...】` header lines after the existing `【mode: ...】` line in all 5 chat branches, with provider-specific score so the fallback branch correctly reflects the `-0.2` penalty
- The `confidence` parameter is accepted for forward compatibility but not weighted in the current scoring (matches task contract)
- No changes to `MESAnalysisOutput` schema, chain construction, retrieval, memory, routing, query rewrite, evaluation script, or UI

## 2026-04-13 — Phase 4.6: Query Rewrite Layer

- New helper `rewrite_query(query, query_class) -> str` — pure heuristic, no LLM call, no new deps
- Rewrite strategy per Phase 3 query class:
  - `case-based` → appends `"半導體製程異常分析 anomaly root cause process deviation"` vocabulary
  - `sop_doc` → appends `"SOP 標準作業程序 規範 spec procedure guideline"` vocabulary
  - `general` → no-op (conservative, avoids over-expansion)
- Original query is always preserved verbatim at the head of the rewritten string, so layer / machine / anomaly terms stay searchable
- Integration point: after `route_query()`, before chain invocation. Memory retrieval and routing still use the **original** query (memory/routing logic untouched per constraint)
- Chat mode: adds optional `【rewritten_query: ...】` header line only when the rewrite actually differs from the original
- Analysis mode: adds `original_query` + `rewritten_query` to all 5 structured output dicts
- No changes to `MESAnalysisOutput` schema, chain construction, memory logic, routing logic, evaluation script, or UI

## 2026-04-13 — Phase 4.5: Hallucination Control Layer

- Added three additive trustworthiness fields to all structured analysis outputs:
  - `evidence_sources: list[str]` — e.g. `["memory:MEM-001", "rag:multi-query-retriever"]`
  - `confidence_reason: str` — short human-readable explanation referencing memory match, routing, fallback, and model confidence
  - `uncertainty_flag: bool` — true when the answer may be weakly grounded (no memory hit + route=llm, fallback provider in use, or general-type answer with low confidence)
- New helper `compute_trust_signals()` derives the three fields from signals already in the request path (mem_ids, route_used, provider_used, `result.anomaly_type`, `result.confidence`). No new retrieval, no new LLM call, no new dependencies.
- Trust signals injected via `output.update(...)` immediately before `json.dumps` in all 5 analysis branches (gemini / openai / auto-gemini / auto-openai-fallback / openai-only).
- Fixed a latent omission: the nested `openai-fallback` branch in auto mode was missing Phase 3's `route_used` / `decision_reason` fields (the earlier `replace_all` pass did not match its deeper indent). Now consistent with the other 4 branches.
- No changes to `MESAnalysisOutput` schema, chain construction, retrieval, memory, routing, UI, evaluation script, or existing fields.

## 2026-04-13 — Phase 4: Evaluation Layer (MVP)

- Added local evaluation utility under `eval/` — not wired into runtime or UI
- New `eval/eval_cases.json` — 10 labeled cases covering 3 categories: memory-hit anomaly (5), SOP/doc (2), general no-memory (3)
- New `eval/run_eval.py` — loads cases, runs the existing analysis path via `run_analysis_with_mode(mode="auto")`, reports:
  - `total_cases`, `llm_responses_parsed`
  - `anomaly_type_accuracy` (LLM decision quality)
  - `memory_used_accuracy` (memory retrieval correctness)
  - `route_used_accuracy` (Phase 3 routing correctness)
- Memory / route metrics computed directly via `retrieve_memory()` + `route_query()` so they remain meaningful even without API keys
- Respects existing `rate_limit()` by sleeping 2.1s between cases
- Writes `eval/eval_results.json` with full per-case detail for run-to-run diffing
- No new dependencies; no changes to `app.py`, chain logic, retrieval, memory, routing, UI, or output schema

## 2026-04-13 — Phase 3: Decision Routing Layer

- Added `classify_query()` — pure heuristic classifier returning `"case-based"`, `"sop_doc"`, or `"general"` (no LLM call, no new deps)
- Added `route_query()` — returns `(route_used, decision_reason, query_class)`:
  - `memory` → memory retrieval matched the query
  - `rag` → SOP/doc query, RAG retrieval dominates
  - `llm` → fallback (general question, no memory hit)
- Chat mode: injects `【route_used: ...】` / `【decision_reason: ...】` into existing header (additive, no schema break)
- Analysis mode: adds `route_used` + `decision_reason` fields to all 5 output dicts alongside Phase 2 fields
- Routing is a debug signal only — underlying chains (memory + RAG + LLM) are unchanged
- No changes to `MESAnalysisOutput` schema, chain construction, retrieval logic, memory layer, or UI

## 2026-04-13 — Phase 2: Structured Decision Output

- Added `SCHEMA_VERSION = "1.0"` constant and `"schema_version"` field to all 5 analysis output dicts
- Added `"validation_passed"` field (bool) to all 5 analysis output dicts
- New helper `invoke_analysis_validated()` wraps `invoke_with_retry`:
  - Preserves existing network-retry behavior unchanged
  - Adds ONE additional retry specifically on parse/validation errors (catches `pydantic.ValidationError`, output-parser exceptions, or error text matching parse-error markers)
  - Returns `(result, validation_passed)` — `True` if first attempt succeeded, `False` if a retry was needed
- Added `ValidationError` to the existing `pydantic` import (additive only)
- No changes to `MESAnalysisOutput` schema fields, existing chain structure, prompt templates, retrieval logic, memory layer, or UI

## 2026-04-13 — Phase 1: Memory observability signals

- Added `memory_used` and `matched_case_ids` debug signals to both `run_chat_with_mode` and `run_analysis_with_mode`
- Chat mode: prepends `【memory_used: true/false】` and `【matched_case_ids: ...】` header to successful responses
- Analysis mode: adds `memory_used` (bool) and `matched_case_ids` (list) as additive fields in JSON output
- No changes to chain structure, retrieval logic, prompt templates, or existing `MESAnalysisOutput` fields

## 2026-04-12 — Phase 1: Memory-based RAG

- Added `memory/memory_store.json` with 5 seed records (thickness_ood, particle_count, etch_rate_drift, uniformity_fail, sheet_resistance)
- Added memory layer to `app.py` (additive only):
  - `load_memory()` — loads records at startup
  - `retrieve_memory(query, top_k=2)` — keyword-token overlap scoring
  - `format_memory_context(records)` — formats `[相關歷史案例]` block
- Memory injected into both `run_chat_with_mode` and `run_analysis_with_mode` via `effective_message` / `effective_description`
- No changes to chain structure, prompt templates, or `MESAnalysisOutput` schema
- Updated `PROMPT_DESIGN.md` to document memory injection format

## 2026-04-11 — Baseline

- Repo initialized as standalone RAG / LLM decision core project
- Initial working version of `app.py` pushed to GitHub:
  - Multi-Query RAG over `rag_data/*.md`
  - Gemini primary / OpenAI fallback provider routing
  - Structured output via `MESAnalysisOutput` (Pydantic)
  - Gradio demo UI
- Scope boundaries clarified: this repo handles RAG / LLM reasoning only
- `AI_ROADMAP` renamed to `AI_ROADMAP.md`
- Docs prepared for long-term development:
  - `README.md` rewritten with scope, run steps, roadmap summary
  - `AI_ROADMAP.md` expanded with Phase 0–8
  - `ARCHITECTURE.md` defines integration boundaries
  - `CLAUDE.md` created with development rules
