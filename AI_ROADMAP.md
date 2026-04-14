# AI Roadmap — RAG / LLM Decision Core

## Scope

**In scope:** RAG retrieval, LLM reasoning, memory retrieval, structured output, evaluation, provider routing, cloud serving.
**Out of scope:** AOI vision, MES ingestion, MES dashboard, machine utilization logic.

---

## Phase 0: Repo Foundation

**Objective:** Clean, scoped repo with documented structure and development rules.

**Why it matters:** A disciplined foundation prevents scope creep and makes each future phase reviewable.

**Acceptance criteria:**
- README defines scope clearly
- CLAUDE.md constrains future development behavior
- ARCHITECTURE.md explains integration boundaries
- AI_ROADMAP.md is the single authoritative roadmap file

---

## Phase 1: Memory-based RAG

**Objective:** Extend RAG retrieval to include structured memory events (historical anomaly cases) alongside static documents.

**Why it matters:** Static SOP documents alone cannot capture pattern history. Memory injection closes the gap between knowledge retrieval and case-based reasoning.

**Acceptance criteria:**
- `ai_memory_events` schema defined
- Memory records retrievable via similarity search
- Memory context injected into prompt alongside RAG context
- Existing chat and analysis chains unaffected (additive only)

---

## Phase 2: Structured Decision Output

**Objective:** Harden the structured output schema — strict field validation, retry on parse failure, and versioned schema.

**Why it matters:** Downstream systems (MES, dashboards) depend on predictable JSON. Flaky output breaks the integration surface.

**Acceptance criteria:**
- `MESAnalysisOutput` schema validated with Pydantic v2
- Retry logic on structured output parse failure
- Output schema version field present
- Unit tests covering required fields and edge cases

---

## Phase 3: Context Orchestrator

**Objective:** Route incoming queries to the appropriate retrieval source (SOP docs, memory events, FAQ, or combined).

**Why it matters:** Not every query needs all context sources. Smart routing reduces noise, latency, and token cost.

**Acceptance criteria:**
- Query classifier routes to: docs-only, memory-only, or combined
- Routing logic is explicit and testable
- Context assembly is auditable in logs

---

## Phase 3+ / Phase 4 — Advanced RAG & Decision System

**Status:** Planning. Scope identified during interview review — gaps the current Phase 1–3 stack does not yet cover.

**Objective:** Move the system from "working prototype with structured output" to a measurable, production-grade retrieval and decision pipeline.

**Why it matters:** The current stack retrieves and answers, but has no feedback loop for retrieval quality, no benchmark for decision accuracy, and no handling of real-world source formats (PDF, images, scanned SOPs). Without these, quality drift is invisible and source coverage is artificially limited to pre-cleaned markdown.

### Work items

**1. Retrieval quality improvements**
- Tune `top_k` per query class (case-based vs. SOP/doc vs. general)
- Add a reranking stage (cross-encoder or LLM-based) between vector recall and context assembly
- Track retrieval diversity so near-duplicate chunks do not crowd out complementary sources

**2. Evaluation system**
- Curate a labeled benchmark dataset of anomaly descriptions → expected `anomaly_type` / root cause / action
- Track retrieval metrics (recall@k, MRR) and decision metrics (field-level accuracy, schema validity rate)
- Runnable as an offline script; results versioned so regressions are visible across phases

**3. Query rewrite layer**
- LLM-based rewrite that normalizes engineer shorthand, expands abbreviations, and resolves implicit context (layer, machine, step)
- Runs before retrieval; rewrite output logged for audit
- Must not replace MultiQueryRetriever — it augments the input, not the retrieval strategy

**4. Multi-source routing refinement**
- Evolve Phase 3's heuristic `classify_query` / `route_query` into a learned or confidence-weighted decision
- Allow routing to *combine* sources with explicit weights rather than picking one dominant source
- Expose routing confidence as a debug field alongside `route_used`

**5. Multimodal support**
- PDF ingestion pipeline (layout-aware parsing, not naive text extraction)
- Image + OCR path for scanned SOPs, equipment screenshots, and wafer map captures
- Normalize multimodal sources into the same chunk + metadata shape the text RAG pipeline already consumes, so downstream chains stay unchanged

### Acceptance criteria
- Benchmark dataset exists and CI-runnable evaluation script reports retrieval + decision metrics
- Reranking stage measurably improves recall@k on the benchmark vs. the Phase 1 baseline
- Query rewrite layer is toggleable and its effect measurable on the benchmark
- Routing decision includes a confidence score; combined-source routing is supported
- At least one non-markdown source format (PDF or image) flows end-to-end into a structured answer

### Out of scope for this phase
- Online learning / fine-tuning
- Changes to `MESAnalysisOutput` schema (breaking changes deferred to a future `2.0` bump)
- AOI vision integration or MES runtime ingestion (belongs in separate repos per Phase 0 scope)

---

## Phase 4: Evaluation Layer

**Status:** In progress — MVP landed. A local evaluation harness (`eval/run_eval.py` + `eval/eval_cases.json`) now reports `anomaly_type_accuracy`, `memory_used_accuracy`, and `route_used_accuracy` against a small labeled dataset. Remaining work: retrieval-level metrics (recall@k, MRR), larger benchmark set, and CI integration — tracked under Phase 3+ / Phase 4 Advanced RAG.

**Objective:** Add automated quality metrics for retrieval relevance and decision accuracy.

**Why it matters:** Without evaluation, there is no signal for whether improvements are real or regressions are introduced.

**Acceptance criteria:**
- Retrieval evaluation: top-k recall against a labeled test set
- Decision evaluation: structured output accuracy on sample anomaly cases ✅ (MVP)
- Evaluation script runnable independently ✅ (MVP)

---

## Phase 6: Retrieval Quality Improvement

**Status:** Implemented (heuristic MVP — token-overlap rerank). Stronger retrieval quality work is split into near-term and long-term buckets below.

**Objective:** Improve retrieval ordering and observability without replacing the vector retriever or adding a new model dependency.

**Why it matters:** MultiQueryRetriever boosts recall by generating 3 sub-queries, but the resulting docs are concatenated in an order that reflects neither query relevance nor diversity. A simple token-overlap rerank surfaces the most query-relevant chunks first, which matters because the LLM's effective context budget is dominated by the earliest chunks in the prompt. Debug signals let downstream consumers and evaluators see what the retriever actually produced.

**Acceptance criteria:**
- Rerank step runs after every retriever without touching the retriever itself ✅
- Debug signals (`retrieved_count`, `reranked_count`, `top_sources`) exposed on analysis output ✅
- Zero new dependencies ✅
- Memory, routing, rewrite, trust, schema, and UI untouched ✅

### Already planned next improvements (near-term)

These are the concrete next steps that build directly on the Phase 6 MVP. Each is sized to fit the minimal-diff / additive-only discipline:

1. **Reranking** — replace or augment the token-overlap scorer with a cross-encoder (e.g. `bge-reranker-base`) once a measurement harness proves it helps. Gated behind a flag so the heuristic remains the fallback.
2. **Provenance / citation-grade evidence** — plumb real retrieved `Document` source paths and chunk offsets into `evidence_sources`, replacing the current `"rag:multi-query-retriever"` placeholder. Requires threading docs from the rerank stage to the output builder.
3. **Multimodal document support** — accept PDF / image / scanned SOP inputs in the retrieval pipeline so source coverage isn't limited to pre-cleaned markdown. Extends `rag_data/` loaders without changing chain structure.
4. **Stronger evaluation metrics** — extend `eval/run_eval.py` with recall@k, MRR, and per-class accuracy, graded against the Phase 4 labeled set. Needed before any rerank change can claim a real improvement.
5. **Confidence calibration** — measure and correct the LLM-reported `confidence` field against eval outcomes, then wire the calibrated value into `compute_trust_score` (currently the `confidence` parameter is accepted but unweighted).

### Long-term roadmap additions

Larger workstreams that require dedicated design and likely touch more than one file at a time. These are explicitly out of scope for a minimal-diff phase:

1. **Multimodal document understanding** — layout-aware PDF parsing, image + OCR pipeline for wafer maps and equipment screenshots, and a normalized chunk + metadata shape that downstream chains can consume without modification.
2. **Document ingestion pipeline** — a standalone ingestion path (source crawl → parse → chunk → embed → index) that can be run offline and versioned separately from the serving code. Enables adding new sources without touching `app.py`.
3. **Golden benchmark / expert-labeled evaluation set** — engineer-reviewed labels on real anomaly cases, with inter-rater agreement tracked. This is the only way to grade *decision quality* at the level MES consumers actually care about.
4. **Consumer-side trust gating** — downstream surfaces (MES dashboard, operator UI) consume `trust_score` / `uncertainty_flag` / `evidence_sources` as first-class inputs to decide whether to display, warn, or suppress a recommendation. Requires an integration contract with the consuming repo, not just additive fields here.

---

## Phase 4.6: Query Rewrite Layer

**Status:** Implemented (heuristic MVP). LLM-based rewrite deferred to Phase 3+/Phase 4 Advanced RAG.

**Objective:** Improve retrieval recall on short or ambiguous queries by expanding them with class-specific engineering vocabulary before they hit the vector store.

**Why it matters:** Engineer shorthand (`"ILD 偏薄"`, `"PVD 靶材"`) often lacks enough surface terms for the multilingual embedding model to land on the right chunks. A small deterministic vocabulary expansion is cheap insurance.

**Acceptance criteria:**
- `rewrite_query()` pure heuristic, no LLM, no new deps ✅
- Used only for retrieval/context — never replaces user-visible input ✅
- Original query preserved verbatim at head of rewritten string ✅
- Memory and routing logic untouched ✅
- Structured output exposes `original_query` + `rewritten_query` ✅

**Deferred to later phases:**
- LLM-based rewrite (resolves implicit context like layer / machine / step)
- A/B measurement of rewrite impact on `route_used_accuracy` and `anomaly_type_accuracy` from Phase 4 eval
- Per-class vocabulary tuning against the Phase 4 benchmark

---

## Phase 4.5: Hallucination Control / Trust Layer

**Status:** Implemented. Additive-only trust signals landed on every structured analysis output.

**Objective:** Give downstream consumers a minimal trust surface without refactoring retrieval or adding a second LLM pass.

**Why it matters:** A structured decision without provenance is indistinguishable from a hallucination. Exposing *what grounded the answer* (memory / RAG), *why confidence is what it is*, and *when the answer may be unreliable* lets MES and human reviewers triage outputs without reading the full context.

**Acceptance criteria:**
- `evidence_sources`, `confidence_reason`, `uncertainty_flag` present on all analysis outputs ✅
- No changes to `MESAnalysisOutput` Pydantic schema ✅
- No new retrieval, no new LLM calls, no new dependencies ✅
- Existing chat / analysis / eval paths unaffected ✅

**Deferred to later phases:**
- Plumbing concrete RAG doc source paths into `evidence_sources` (requires chain refactor to thread retrieved docs through to the output stage)
- Calibrated confidence scoring (Phase 5 Decision Engine)
- LLM-as-judge validation of `confidence_reason` coherence

---

## Phase 5: Decision Engine / Trust Layer

**Status:** Trust scoring landed (heuristic MVP). Ranking of root-cause candidates and reasoning-field generation remain open.

**Objective:** Add ranking, confidence scoring, and basic explainability to the LLM output.

**Why it matters:** A bare LLM answer is not an auditable engineering decision. Ranking and explanation make the output trustworthy.

**Acceptance criteria:**
- Trust score / trust level / trust reason attached to every structured analysis output ✅
- Trust score / trust level surfaced in chat-mode header across all 5 branches ✅
- Root cause candidates ranked by confidence (deferred)
- Recommended actions include reasoning field (deferred)
- Confidence threshold configurable (deferred)

**Deferred to later phases:**
- Calibrate baseline and deltas against Phase 4 evaluation dataset
- Weight `confidence` into the score once LLM-reported confidence is calibrated (Phase 3+/4 Advanced RAG)
- LLM-as-judge validation of `trust_reason` coherence

---

## Phase 6: Reliability / Provider Routing

**Objective:** Formalize multi-provider routing with health checks, circuit breaker, and fallback policy.

**Why it matters:** Production use requires the system to degrade gracefully, not fail silently.

**Acceptance criteria:**
- Provider health check endpoint
- Circuit breaker with configurable threshold
- Fallback chain: Gemini → OpenAI → cached response
- Provider selection logged per request

---

## Phase 7: Cloud-ready Deployment

**Objective:** Replace the Gradio demo with a FastAPI serving layer deployable to cloud infrastructure.

**Why it matters:** The Gradio app is a prototype tool. A proper API layer enables integration with MES runtime and future clients.

**Acceptance criteria:**
- FastAPI app exposes `/chat` and `/analyze` endpoints
- API schema matches `MESAnalysisOutput`
- Docker container builds and runs locally
- Gradio UI remains available as a dev tool

---

## Phase 8: Document Normalization

**Objective:** Normalize all knowledge source documents — consistent format, tagging, and versioning.

**Why it matters:** RAG quality depends on document quality. Inconsistent source docs produce inconsistent retrieval.

**Acceptance criteria:**
- All `rag_data/` documents follow a defined template
- Documents tagged with: type (SOP / FAQ / OCAP / FMEA), version, layer
- Stale documents identified and flagged
