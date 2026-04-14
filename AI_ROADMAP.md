# AI Roadmap — RAG / LLM Decision Core

## Scope

**In scope:** RAG retrieval, LLM reasoning, memory retrieval, structured output, evaluation, provider routing, cloud serving.
**Out of scope:** AOI vision, MES ingestion, MES dashboard, machine utilization logic.

---

## Status Index

This index is the single source of truth for phase state. Individual phase sections below carry detail; this table is how to answer "what's done?" without reading the whole file.

### ✅ Implemented

| Phase | Name | Artifact |
|---|---|---|
| 0 | Repo Foundation | README / CLAUDE.md / ARCHITECTURE.md |
| 1 | Memory-based RAG | `memory_store.json` + `retrieve_memory()` |
| 2 | Structured Decision Output | `MESAnalysisOutput` + `invoke_analysis_validated()` + `schema_version` |
| 3 | Routing / Context Orchestrator | `classify_query()` + `route_query()` + `route_used` / `decision_reason` debug |
| 4 | Evaluation Layer (MVP) | `eval/run_eval.py` + `eval/eval_cases.json` (10 cases) |
| 4.5 | Hallucination Control / Trust Signals | `evidence_sources` / `confidence_reason` / `uncertainty_flag` |
| 4.6 | Query Rewrite (heuristic) | `rewrite_query()` + `original_query` / `rewritten_query` |
| 5 | Trust Layer (scoring) | `compute_trust_score()` + `trust_score` / `trust_level` / `trust_reason` (analysis + chat) |
| 6 | Retrieval Quality / Rerank | `rerank_docs()` + `make_rerank_retriever()` + `retrieved_count` / `reranked_count` / `top_sources` |
| 6.5 | Retrieval Evaluation Metrics | `expected_sources` labels + `retrieval_hit_rate` / `top_k_hit_rate` / `avg_source_overlap` in eval summary |

### 🔜 Near-term next work (planned)

- **Phase 6.6** — A/B measurement of rewrite and rerank against Phase 6.5 metrics
- **Near-term engineering backlog** (see dedicated section) — chunking strategy, embedding selection, cross-encoder rerank, larger benchmark, multimodal RAG

### 🗺 Long-term roadmap

- **Phase 7** — Cloud-ready FastAPI serving layer
- **Phase 8** — Document normalization + ingestion pipeline
- **Phase 9** — Reliability / provider routing with circuit breaker
- Multimodal document understanding (layout-aware PDF, image+OCR)
- Golden benchmark with expert labels + inter-rater agreement
- Consumer-side trust gating on MES/dashboard surfaces

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

**Status:** MVP landed. A local evaluation harness (`eval/run_eval.py` + `eval/eval_cases.json`) reports `anomaly_type_accuracy`, `memory_used_accuracy`, and `route_used_accuracy` against a small labeled dataset. Retrieval-level metrics shipped in Phase 6.5. Larger benchmark set and CI integration remain open.

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

## Phase 6.5: Retrieval Evaluation Metrics

**Status:** Implemented. `eval/run_eval.py` reads the Phase 6 retrieval debug fields from every analysis output and grades retrieval quality against per-case `expected_sources` labels.

**Objective:** Make retrieval quality a first-class measurement surface so rerank and rewrite changes can be graded against concrete deltas instead of anecdotes.

**Why it matters:** Phase 6 shipped a rerank layer with no way to tell whether it helps. Phase 6.5 closes that loop — each eval case carries an optional `expected_sources` list, and the runner reports per-case `retrieval_hit` / `top_k_hit` / `source_overlap` plus aggregate `retrieval_hit_rate`, `top_k_hit_rate`, `avg_source_overlap`, `avg_retrieved_count`, `avg_reranked_count`.

**Acceptance criteria:**
- `expected_sources` added as an additive optional label on eval cases ✅
- Per-case metrics (`retrieval_hit`, `top_k_hit`, `source_overlap`) ✅
- Aggregate metrics in the run summary and per-case table ✅
- `app.py` unchanged (eval-only extension) ✅

**Known limitations (honest baseline):**
- Only 7 of 10 cases carry `expected_sources` labels; 3 general-knowledge cases are ungraded
- Labels are hand-assigned by a single author, not inter-rater validated
- `top_k_hit` equals `retrieval_hit` by construction today (`top_sources` is already the top-k window from `app.py`)
- 10-case baseline is too small to distinguish a real rerank improvement from noise — one mis-retrieval swings `retrieval_hit_rate` by ~14 points

---

## Phase 6.6: Retrieval A/B Measurement

**Status:** Planned. Recommended next coding phase.

**Objective:** Use the Phase 6.5 metric surface to measure the actual contribution of each retrieval-quality layer shipped so far (query rewrite, rerank), so we can defend keeping them, tuning them, or replacing them.

**Why it matters:** Query rewrite (Phase 4.6) and rerank (Phase 6) are both "always on" today. We believe they help — the heuristic smoke tests look right — but Phase 6.5 gives us a single point estimate with no counterfactual. Without an A/B measurement, claims like "rerank improves retrieval" are just opinions.

**Scope:**
1. Add an eval-only toggle surface — environment variables or CLI flags on `eval/run_eval.py` — that disables `rewrite_query` and/or `make_rerank_retriever` at eval time. The runtime (`app.py`) default behavior does not change.
2. Run the eval four times covering the full 2×2 grid:
   - `(rewrite off, rerank off)` — baseline
   - `(rewrite on, rerank off)` — rewrite contribution
   - `(rewrite off, rerank on)` — rerank contribution
   - `(rewrite on, rerank on)` — current production behavior
3. For each run, record `retrieval_hit_rate`, `top_k_hit_rate`, `avg_source_overlap`, `anomaly_type_accuracy`, `avg_retrieved_count`, `avg_reranked_count`.
4. Produce a before/after comparison table in a reproducible artifact (`eval/eval_ab_results.md` or similar) showing the delta attributable to each layer.

**Acceptance criteria:**
- A/B toggle exists and is strictly eval-only (runtime path unaffected)
- Four-run comparison table committed as a reproducible artifact
- Each layer's contribution is stated as a quantitative delta, not qualitative prose
- Any layer showing zero or negative impact on the primary metrics is flagged for redesign or removal

**Out of scope for this phase:**
- Changing the layers themselves in response to results (that is a follow-up phase)
- Statistical significance testing — the dataset is too small; deferred to the larger benchmark work in the engineering backlog

### Current limitations (as of this phase)

These are the honest constraints on what Phase 6.6 numbers can be used to claim. Any external communication about retrieval quality should be scoped to these bounds.

- **Benchmark is small.** 40 cases total, 37 graded. Standard error on rate metrics is wide enough that 5-point deltas can be noise rather than real improvements.
- **Labels are hand-assigned.** `expected_sources` mappings were authored by a single person against topical guesswork, not against a gold retriever or inter-rater review. Anomaly and equipment tags are lowest-reliability.
- **Mocked runs validate the framework, not model performance.** The smoke tests in this repo exercise the A/B toggle plumbing and the metric computation; they do not produce numbers attributable to the live LLM stack. Any number printed by a mocked run must not be cited as a real accuracy figure.
- **Regression-detection oriented.** The current harness is well suited to catching "did change X make the stack worse?" across a controlled diff. It is not suited to certifying production accuracy, ranking models against public baselines, or supporting go/no-go deployment decisions.

### Next step (recommended)

Before pursuing any further retrieval-layer work (cross-encoder rerank, embedding swap, chunking changes), the benchmark itself must grow:

1. **Expand the benchmark dataset** to 100+ curated cases, stratified by anomaly type, severity, and layer. Each new case requires an `expected_sources` label reviewed by someone other than the author. Target: inter-rater agreement ≥ 0.8 on a random 20% sample.
2. **Run real A/B testing** on the expanded dataset against live LLM providers (Gemini + OpenAI). Record per-mode numbers in a reproducible artifact committed alongside the dataset. Until this is done, no strong accuracy claim about any retrieval layer is defensible.
3. **Gate further retrieval changes** behind a measurable improvement on the expanded benchmark. A cross-encoder rerank that cannot beat token-overlap on real data does not ship.

---

## Near-term engineering backlog

This is the concrete work the team is most likely to pick up after Phase 6.6 finishes. Each item is sized to fit the minimal-diff / additive-only discipline, and each unblocks something on the long-term roadmap.

### 1. Chunking strategy

**What:** Revisit `RecursiveCharacterTextSplitter` parameters (`chunk_size=600`, `chunk_overlap=80`, Chinese-aware separators) against the Phase 6.5 metric surface. Measure `retrieval_hit_rate` under 3–4 alternative configurations (smaller chunks for SOP steps, larger chunks for FMEA narrative, overlap tuning).

**Why:** The current chunking was chosen once and never measured. It almost certainly over-chunks short SOP procedures and under-chunks FMEA tables. Chunk boundaries directly cap how much of a relevant passage the rerank step can surface.

**Unblocks:** Fair comparison with cross-encoder rerank — without decent chunks, a better reranker has nothing to rank.

### 2. Embedding model selection / tuning

**What:** Benchmark alternatives to the current `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` on the Phase 6.5 dataset. Candidates include `bge-m3`, `gte-multilingual-base`, and newer multilingual E5 variants. Optionally fine-tune on the Phase 4 labeled set once it grows.

**Why:** The current embedding model was chosen for CPU-friendliness, not retrieval quality on semiconductor vocabulary. A model that understands `"ILD"`, `"PECVD"`, `"uniformity"` as related concepts directly lifts `retrieval_hit_rate` with zero changes to the rest of the chain.

**Unblocks:** Cross-encoder rerank quality (better candidates in, better ranking out), and multimodal RAG (shared embedding space for text + image captions).

### 3. Cross-encoder reranker

**What:** Replace the Phase 6 token-overlap rerank with a learned cross-encoder (`bge-reranker-base` or `bge-reranker-v2-m3`). Gate behind a flag so the heuristic remains the fallback. Measure Phase 6.5 metric deltas before/after.

**Why:** Token-overlap rewards surface-term matches and misses semantic synonyms. A cross-encoder scores query-document relevance directly and consistently beats lexical methods on non-English technical corpora.

**Unblocks:** Defensible trust scoring — once rerank actually selects the right docs, `evidence_sources` becomes citation-grade, and `trust_score` deltas track retrieval quality instead of being dominated by the memory-hit boolean.

### 4. Larger benchmark dataset

**What:** Grow `eval/eval_cases.json` from 10 to 100+ cases. Stratify by anomaly type, severity, and layer. Record source provenance for every case (`expected_sources` populated throughout, not just 7 of 10).

**Why:** 10 cases cannot distinguish a real 5-point retrieval improvement from noise. 100+ cases make small rerank / embedding deltas visible and let us compute per-stratum accuracy (does rerank hurt SOP queries while helping case-based queries?).

**Unblocks:** Statistical claims about any layer's contribution — the blocker Phase 6.6 explicitly defers. Also unblocks the "golden benchmark" long-term item by serving as the first curated version.

### 5. Multimodal RAG (PDF / image / OCR)

**What:** Add a non-markdown ingestion path. Layout-aware PDF parsing (e.g. `pymupdf` + heuristic section detection), image OCR for scanned SOPs and wafer map captures, normalized into the same `Document` shape the existing chain consumes. No changes to chains or prompts — new source format only.

**Why:** Real FAB documentation lives in PDFs and scanned images, not pre-cleaned markdown. Until the ingestion pipeline can absorb those sources, the retrieval layer is artificially limited to whatever someone hand-converts into `rag_data/`.

**Unblocks:** The entire "long-term multimodal document understanding" roadmap item. Also lets trust signals cite real production documents instead of demo markdown.

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

## Phase 9: Reliability / Provider Routing

**Status:** Planned — long-term. Renamed from the original "Phase 6" to avoid collision with the Phase 6 retrieval quality work that shipped first.

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
