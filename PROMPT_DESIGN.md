# Prompt Design

This file documents the prompt templates used in `app.py` and future iterations.

---

## Current prompts (app.py)

### Chat prompt (freeform Q&A)

- System: FAB Copilot knowledge assistant, answer only from knowledge base context, Traditional Chinese, cite specific values and steps
- Human: `{question}`
- Context variable: `{context}` — formatted RAG chunks with source labels

### Analysis prompt (structured output)

- System: Anomaly analysis expert, output structured analysis matching `MESAnalysisOutput` schema
- Human: `{question}` (anomaly description)
- Context variable: `{context}` — same RAG chunks
- `anomaly_type` constrained to: `thickness_ood / particle_count / sheet_resistance / uniformity_fail / etch_rate_drift / cd_shift / void_detected / general`

### Multi-Query expansion prompt

- Generates 3 alternative search queries per question to improve retrieval recall
- Language: Traditional Chinese
- Role framing: semiconductor process expert

---

## Phase 1 memory injection (implemented)

Memory is injected **before the question** in the user turn, not in the system prompt.
This avoids changing the chain structure or adding new prompt template variables.

Format prepended to `effective_message` / `effective_description`:

```
[相關歷史案例]
- [MEM-001] thickness_ood / ILD / PECVD-01: <summary> | 根因: <root_cause> | 處置: <action_taken> | 結果: <outcome>
- [MEM-002] ...

---

<original user question or anomaly description>
```

The `[相關歷史案例]` block is only included when `retrieve_memory()` returns ≥ 1 result.
Retrieval is keyword-token overlap scoring across: `anomaly_type`, `layer`, `machine_id`, `summary`, `root_cause`.
Top-k = 2 by default. Memory records live in `memory/memory_store.json`.

## Debug signals (observability)

Both `run_chat_with_mode` and `run_analysis_with_mode` emit two non-LLM debug signals derived from memory retrieval:

- `memory_used` — `True` if `retrieve_memory()` returned ≥ 1 record
- `matched_case_ids` — list of `case_id` values from the matched records

Chat mode prepends them as header lines before `【provider_used: ...】`:

```
【memory_used: true】
【matched_case_ids: MEM-001, MEM-002】
【provider_used: gemini-2.5-flash】
【mode: auto】

<LLM answer>
```

Analysis mode adds them as additive JSON fields (`memory_used`, `matched_case_ids`) alongside the existing `MESAnalysisOutput` fields. No schema field is removed or renamed.

## Phase 2 structured output hardening (implemented)

Analysis output JSON now includes two additive metadata fields:

- `schema_version` — currently `"1.0"`, bumped when a breaking schema change ships
- `validation_passed` — `true` if the first LLM call returned valid structured output; `false` if a parse-error retry was needed (and succeeded)

**Retry behavior:**
- Network / quota errors: handled by existing `invoke_with_retry` (unchanged)
- Parse / validation errors (`pydantic.ValidationError`, output-parser exceptions, or matching markers like `"failed to parse"`, `"json"`, `"schema"`, `"missing"`, `"invalid"`): retried exactly ONCE via `invoke_analysis_validated()`
- If both attempts fail, the existing outer error path returns an error string — no output dict is emitted

The Pydantic `MESAnalysisOutput` schema itself is unchanged. `schema_version` and `validation_passed` are added to the output dict only, preserving strict schema adherence.

## Phase 3 decision routing layer (implemented)

A lightweight heuristic routing step runs before the chain is invoked. It does not rewrite prompts or change which chain executes — it produces two debug signals that expose *why* a particular knowledge source dominated the answer.

**Query classification (`classify_query`)** — pure string heuristic, no LLM:
- `case-based` — query mentions anomaly markers (`異常`, `偏`, `OOD`, `drift`, `fail`, …)
- `sop_doc` — query mentions SOP/spec markers (`SOP`, `規範`, `規格`, `流程`, `spec`, `procedure`, …)
- `general` — everything else

**Routing decision (`route_query`)** — returns `(route_used, decision_reason, query_class)`:
- `memory` — memory layer returned at least one matching case
- `rag` — `sop_doc` query with no memory hit; RAG retrieval dominates
- `llm` — fallback: general question, no memory hit

**Debug fields:**
- Chat mode: adds `【route_used: ...】` / `【decision_reason: ...】` to the existing header block
- Analysis mode: adds `route_used` and `decision_reason` as additive JSON fields alongside Phase 2 fields

Routing is observational only. The chain itself still wires memory context + RAG retrieval + LLM together unchanged, preserving the Phase 1/2 contract. `MESAnalysisOutput` schema is untouched.

## Phase 4.5 hallucination control / trust signals (implemented)

Three additive metadata fields now accompany every structured analysis output. They are derived **post-LLM, pre-serialization** from signals already present in the request path — no new retrieval, no second LLM pass, and no prompt rewriting.

- **`evidence_sources: list[str]`** — provenance markers for what actually fed the answer:
  - `"memory:<case_id>"` for each memory record that matched the query
  - `"rag:multi-query-retriever"` when `route_used == "rag"` (placeholder until doc source names are plumbed end-to-end; listing concrete doc paths requires refactoring the chain and is deferred to a future phase)
  - Empty list `[]` if neither source contributed
- **`confidence_reason: str`** — human-readable explanation composed from existing signals:
  - memory match on N historical case(s)
  - routed to SOP/doc retrieval, no memory match
  - no memory hit, relying on LLM + general RAG context
  - appended with `"fallback provider used"` when `provider_used` contains `"fallback"`
  - appended with `"low model confidence"` when `result.confidence < 0.5`
- **`uncertainty_flag: bool`** — additive heuristic:
  - `True` if `route_used == "llm"` and no memory hit (weak grounding)
  - `True` if the fallback provider was used (primary provider failed)
  - `True` if `anomaly_type == "general"` and `confidence < 0.6`
  - otherwise `False`

All Phase 1/2/3 fields (`memory_used`, `matched_case_ids`, `schema_version`, `validation_passed`, `route_used`, `decision_reason`) remain unchanged. The Pydantic `MESAnalysisOutput` schema itself is untouched — trust fields are added to the output dict only, preserving strict schema adherence.

## Phase 4.6 query rewrite layer (implemented)

A pure heuristic rewrite step runs between query classification and chain invocation. It does **not** rewrite the prompt template itself — it expands the *retrieval input* with extra vocabulary so that vector recall is more likely to hit relevant chunks, while keeping the original user terms intact.

**Rewrite rules (`rewrite_query`):**
- `case-based` → `"{original} | 半導體製程異常分析 anomaly root cause process deviation"`
- `sop_doc` → `"{original} | SOP 標準作業程序 規範 spec procedure guideline"`
- `general` → no-op (returned unchanged)

**Key properties:**
- Original query is always the leftmost substring of the rewritten output, so layer / machine / anomaly terms remain searchable.
- Memory retrieval still uses the **original** query (memory/routing logic unchanged per phase constraint).
- The rewritten query is used only for RAG retrieval + prompt context. The user-visible input in the Gradio UI is never modified.
- No LLM call is made inside the rewrite step.

**Debug surface:**
- Chat mode: `【rewritten_query: ...】` header line appears only when the rewrite differs from the original.
- Analysis mode: adds `original_query` and `rewritten_query` fields to the structured output dict alongside Phase 1/2/3/4.5 fields.

## Phase 5 decision trust layer (implemented)

A heuristic trust score is computed after the Phase 4.5 trust signals are attached, consuming only fields already on the output dict. It runs post-LLM, pre-serialization — no new retrieval, no new LLM call.

**Scoring (`compute_trust_score`)** — neutral 0.5 baseline, clamped to `[0, 1]`:

| Signal | Delta |
|---|---|
| `matched_case_ids` non-empty | **+0.4** |
| `route_used == "rag"` | **+0.2** |
| `route_used == "llm"` | **−0.2** |
| `"fallback" in provider_used` | **−0.2** |
| `evidence_sources` non-empty | **+0.2** |

**Bucketing:**
- `HIGH` — `trust_score ≥ 0.75`
- `MEDIUM` — `0.5 ≤ trust_score < 0.75`
- `LOW` — `trust_score < 0.5`

**Analysis mode — fields added to output dict:**
- `trust_score: float` (2-decimal)
- `trust_level: str`
- `trust_reason: str` — `"; "`-joined list of deltas that fired

**Chat mode — header trace:**
- Adds `【trust_score: ...】` + `【trust_level: ...】` lines after the existing `【mode: ...】` line in every chat response
- Each branch passes its own `provider_label` (including `"openai-fallback"` in the auto-fallback path) so the `-0.2` fallback delta applies exactly where it should
- `trust_reason` is intentionally omitted from chat mode to keep the header compact — it remains available on the analysis-mode JSON output

The `confidence` parameter is part of the helper signature for forward compatibility but is not weighted in the current scoring rules. All Phase 1/2/3/4.5/4.6 fields (`memory_used`, `matched_case_ids`, `schema_version`, `validation_passed`, `route_used`, `decision_reason`, `evidence_sources`, `confidence_reason`, `uncertainty_flag`, `original_query`, `rewritten_query`) are preserved unchanged. The Pydantic `MESAnalysisOutput` schema itself is untouched.

## Phase 6 retrieval rerank layer (implemented)

A lightweight rerank step runs between the MultiQueryRetriever and `format_docs`, inside every chain wiring. It does **not** replace the vector retriever — it reorders the docs the retriever already returned.

**Scoring (`rerank_docs`):**
- Score = token-overlap count between the query and `doc.page_content`, computed with the existing `_tokenize()` helper from the memory layer
- Ties broken by original retrieval order (stable sort via `-i` secondary key)
- Top `N=6` docs kept by default; empty query → first `N` docs returned unchanged

**Why token overlap?** It requires zero new dependencies (no cross-encoder, no reranker model, no API), runs in microseconds per query, and correlates well with MultiQueryRetriever output quality on Chinese + English semiconductor vocabulary. A real cross-encoder rerank is listed as deferred in the Phase 3+/Phase 4 Advanced RAG roadmap.

**Debug surface (analysis mode):**
Every structured analysis output now includes:
- `retrieved_count` — raw doc count from the retriever (before rerank)
- `reranked_count` — docs kept after rerank
- `top_sources` — up to 3 unique source filenames from the top-reranked docs

These values are read from a module-level `_last_retrieval_debug` dict that the rerank wrapper writes during `chain.invoke`. Chat mode is intentionally not wired — the header is already dense and analysis JSON is the natural debug surface.

## Planned prompt changes

- Add explicit reasoning / ranking instructions to analysis prompt (future phase)
