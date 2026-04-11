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

## Planned prompt changes

- **Phase 3:** Add routing logic to select which context blocks to include
- **Phase 5:** Add explicit reasoning / ranking instructions to analysis prompt
