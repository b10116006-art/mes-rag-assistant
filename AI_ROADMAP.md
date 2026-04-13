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

## Phase 5: Decision Engine

**Objective:** Add ranking, confidence scoring, and basic explainability to the LLM output.

**Why it matters:** A bare LLM answer is not an auditable engineering decision. Ranking and explanation make the output trustworthy.

**Acceptance criteria:**
- Root cause candidates ranked by confidence
- Recommended actions include reasoning field
- Confidence threshold configurable

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
