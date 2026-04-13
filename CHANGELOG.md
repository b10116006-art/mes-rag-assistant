# Changelog

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
