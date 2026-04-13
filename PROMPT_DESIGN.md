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

## Planned prompt changes

- **Phase 5:** Add explicit reasoning / ranking instructions to analysis prompt
