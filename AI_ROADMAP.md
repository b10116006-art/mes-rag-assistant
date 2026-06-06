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
| 6.6 | Retrieval A/B Measurement | `eval/eval_ab_results.json` — 4-mode (baseline / rewrite_only / rerank_only / full) × 40 cases |

### 🧪 Experimental — held (not merged)

| Phase | Name | Status | Branch / artifact |
|---|---|---|---|
| 7 (Decision) | Evidence-bound Decision Reasoning prompt | HOLD — strict variant regressed `decision_match` 0.656 → 0.646; retrieval flat | `phase7-prompt-hardening` (preserved as audit trail). See "Decision-Layer Track" section. |

### 🔜 Near-term next work (planned)

- **Phase 6.6** — A/B measurement of rewrite and rerank against Phase 6.5 metrics (✅ Completed — see Implemented table; A/B artifact committed)
- **Course-driven gap items** (G1–G4) — see "Course-driven gap items" section below; scheduled by **dependency**, not by recency
- **Enterprise readiness track** (ENT-1 → ENT-3) — see "Enterprise readiness track" section below
- **Phase 7B — Action Canonicalization Layer** — methodology improvement to normalize semantically-equivalent action phrases inside the scorer, before token-overlap matching. Design captured in `docs/architecture/ADR_007_action_canonicalization.md`. See "Decision-Layer Track" section.
- **Resume-ready Polish Track (Portfolio Packaging)** — packaging-only items (LICENSE, baseline snapshot, A/B chart, README polish, diagram refresh) for outreach. **Not a research phase**; does not replace G2 / G4 / Phase 7B / FastAPI work. See "Resume-ready Polish Track (Portfolio Packaging)" section.
- **Near-term engineering backlog** (see dedicated section) — chunking strategy, embedding selection, cross-encoder rerank, larger benchmark, multimodal RAG

### 🗺 Long-term roadmap

- **Phase 7** — Cloud-ready FastAPI serving layer  _(naming note: distinct from "Phase 7 (Decision)" in the Decision-Layer Track — different scope, same number; disambiguate by renumbering when convenient)_
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

**Status:** ✅ Implemented. A/B artifact committed in `eval/eval_ab_results.json` covering the four modes (baseline / rewrite_only / rerank_only / full) over the 40-case benchmark. (Originally documented as: "Planned. Recommended next coding phase." — preserved here for historical context.)

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

## Course-driven gap items

Net-new items derived from `COURSE_TECH_GAP_ANALYSIS.md` (Apr 2026). They are scheduled by **dependency**, not by recency — see "Dependency-aware execution sequence" below for the full ordering. Each item is sized to the minimal-diff / additive-only discipline and carries explicit upstream blockers so we do not trial multiple changes in parallel and lose attribution.

Items are listed in execution (dependency) order: G2 → G4 → G3 → G1.

### G2 — Metadata filter (`doc_type` tag + Chroma filter)

**What:** Tag every chunk with `doc_type` ∈ {`anomaly`, `sop`, `ai_logic`, `equipment`}. Use the existing `classify_query()` (Phase 3) to set a `where=` filter on Chroma so the retriever only sees chunks of the right type.

**Why:** Today all chunks share one search space. Queries like "ILD 異常處理 SOP" hit anomaly definitions before the actual SOP content. Eval shows ~5 of 40 cases mis-route for this single root cause.

**Dependencies:** None. Independent of Phase 6.6 closeout. **IMMEDIATE.**

**Affects:** `rag_data/` (metadata header), `app.py` (Chroma `where=` plumbing). Schema unchanged.

**Acceptance:** ≥3 of the currently-misclassified cases recover their `expected_sources` hit. No regression on previously-passing cases (gated by G4).

### G4 — Eval baseline regression gate

**What:** Add `eval/run_baseline_check.py` and `eval/baseline_metrics.json`. Run eval, compare against the committed Phase 6.6 baseline, exit non-zero on regression of any tracked metric beyond a configured tolerance.

**Why:** Phase 6.6 produced one baseline. Without a gate, the next change that lowers `retrieval_hit_rate` by 4 points lands silently. This turns the baseline into a contract.

**Dependencies:** Phase 6.6 closeout (need a committed baseline to gate against — ✅ already done). **IMMEDIATE.**

**Affects:** `eval/` only. Runtime path (`app.py`) untouched.

**Acceptance:** Script runs locally, exits 1 on synthetic regression, exits 0 on the current baseline. `baseline_metrics.json` committed alongside the script.

### G3 — LLM-based query rewrite (gated path)

**What:** Add an LLM rewrite path alongside the existing heuristic `rewrite_query()`. Flag-toggleable; the original heuristic remains the default fallback.

**Why:** Phase 4.6's heuristic is deterministic but only handles known vocabulary. An LLM rewrite can resolve implicit context (layer / machine / step) at the cost of an extra LLM call per query. Whether the cost is worth it is an empirical question — needs A/B data on the *expanded* benchmark, not the 40-case set.

**Dependencies:** **Backlog #4** (100+ benchmark) — 40 cases too noisy to detect realistic 3–5 point deltas. Also G4 (regression gate must exist before trialing).

**Affects:** `app.py` — `rewrite_query()` adds an LLM branch behind a flag.

**Acceptance:** A/B comparison vs the heuristic on the 100+ benchmark. Ships only if `retrieval_hit_rate` or `top_k_hit_rate` improves by a margin larger than measurement noise. Otherwise: flag stays off, code stays for future re-eval.

**Cross-reference:** Refines the "LLM-based rewrite (deferred)" bullet under Phase 4.6 — does not replace it.

### G1 — LoRA fine-tune embedding model

**What:** LoRA-adapt the embedding model selected by **backlog #2** on the project's domain corpus + eval positives. New script `scripts/finetune_embedding.py`.

**Why:** Off-the-shelf multilingual embeddings cluster semiconductor terminology poorly — "ILD 異常定義" and "ILD SOP 步驟" land too close in vector space. LoRA injects domain separation without retraining the full model (~333× fewer trainable params).

**Dependencies:** **Backlog #2** (embedding benchmark must select a base model first — fine-tuning the wrong base model is wasted effort). Also backlog #4 (need the larger labeled set as training/validation positives).

**Affects:** New `scripts/finetune_embedding.py`. `app.py` only switches when the adapter is proven on the G4 gate.

**Acceptance:** Adapter beats unaltered base model by a margin larger than noise on `retrieval_hit_rate` and `nDCG@3`. Otherwise: artifact retained, not loaded by `app.py`.

**Cross-reference:** Refines backlog #2 ("Embedding model selection / tuning") — fine-tune is the *tuning* half of that item.

---

## Enterprise readiness track

Net-new items from interview / JD feedback. Strictly serving / ops scope — no business-logic, no AOI, no MES runtime. Sequenced **after** Phase 7 except ENT-1, which can wrap the current Gradio prototype today and update its Dockerfile when FastAPI lands (no throwaway work).

Items listed in execution (dependency) order: ENT-1 → Phase 7 → ENT-2 → ENT-3.

### ENT-1 — Docker

**What:** `Dockerfile` + `docker-compose.yml` wrapping the current Gradio app + Chroma volume. After Phase 7 ships, update the Dockerfile to use the FastAPI entrypoint.

**Why:** Decouples deployment from local Python. Reusable across Phase 7 / ENT-2 / ENT-3. No throwaway work — same Dockerfile evolves in lockstep with the serving layer.

**Dependencies:** None — can run before Phase 7.

**Affects:** Net-new files. No application code change.

### ENT-2 — API auth + rate limiting

**What:** API-key middleware + `slowapi` rate limiting on the FastAPI surface.

**Why:** Bare endpoints are not deployable to a shared environment. Demonstrates awareness of the basic enterprise contract.

**Dependencies:** **Phase 7** (needs FastAPI to exist).

**Affects:** Future `api/main.py`.

### ENT-3 — `/health` + `/metrics`

**What:** Liveness / readiness check + Prometheus-format metrics endpoint (request count, latency histogram, provider usage, error rate).

**Why:** Observable systems are debuggable systems. Required to claim "production-ready" with a straight face.

**Dependencies:** **Phase 7**.

**Affects:** Future `api/main.py`.

---

## Decision-Layer Track (Phase 7 / Phase 7B)

> **Naming note.** This section's "Phase 7" is the Decision-Layer experiment proposed in the architect-review thread (Option A: Evidence-bound Decision Reasoning). The long-term roadmap above also lists a "Phase 7 — Cloud-ready FastAPI serving layer". The two share the number historically; renumber one when convenient. They are independent in scope.

### Phase 7 (Decision Reasoning) — 🧪 Experimental HOLD

**Status:** HOLD — not merged to `main`. Branch `phase7-prompt-hardening` preserved as audit trail.

**Hypothesis:** lift `avg_decision_match` by adding an additive `evidence_to_action` schema field that forces the LLM to cite which retrieved chunk justifies each `recommended_action`. Citation should drag predicted action wording toward verbatim SOP language, raising `action_score` (the dominant component of `decision_match`).

**Experiment:** two prompt variants tested behind `USE_DECISION_REASONING` flag (default `False`):

- **Gentle directive** — ask for grounding; allow `supporting_source:"none"` stubs. Result: `decision_match` 0.656 → 0.660 (+0.004, indistinguishable from noise).
- **Strict directive (this branch)** — R1–R4 hard rules (every action grounded, verbatim SOP wording preferred, ungrounded actions omitted, source excerpt quoted) plus BAD/GOOD few-shot. Result: `decision_match` 0.656 → **0.646 (−0.010)**.

**Retrieval guardrails (Phase 7 must not move these):**

| metric | reasoning OFF | reasoning ON (strict) | Δ |
|---|---|---|---|
| `retrieval_hit_rate` | 0.829 | 0.829 | flat ✅ |
| `top_k_hit_rate` | 0.829 | 0.829 | flat ✅ |
| `avg_mrr` | 0.800 | 0.800 | flat ✅ |
| `avg_ndcg_at_k` | 0.763 | 0.763 | flat ✅ |
| `avg_decision_match` | **0.656** | **0.646** | **−0.010** |

**G4 baseline regression gate:** PASS (delta within ±0.020 threshold) — but the strict prompt is **not a production improvement** and should not be merged on that basis alone.

**Interpretation:** retrieval is no longer the bottleneck. Prompt strictness is the wrong lever — strict R3 ("omit ungrounded actions") over-pruned action generation, and forcing verbatim wording from `rag_data/` chunks sometimes *increased* lexical drift relative to the `expected_actions` labels (which are themselves paraphrased SOP). The real bottleneck is lexical / semantic mismatch between LLM-natural action phrases and benchmark labels, not reasoning quality or grounding discipline.

**Decision:** HOLD. Do not merge the strict prompt change. Keep `phase7-prompt-hardening` branch as an audit trail. The `evidence_to_action` schema field and gentle directive (already on main behind the default-False flag) remain as additive infrastructure with no production behavior change. Pivot to **Phase 7B**.

### Phase 7B (Action Canonicalization Layer) — 🗺 Planned (design phase)

**Status:** Planned. Design captured in `docs/architecture/ADR_007_action_canonicalization.md`. No implementation branch yet — gated on doc sync first.

**Hypothesis:** the residual `decision_match` gap is **lexical equivalence the scorer cannot see**, not reasoning quality. Phrases like `"停止機台"`, `"Hold 設備"`, `"暫停 production"`, `"tool hold"`, and `"設備暫停"` are the same SOP step but score differently under `_action_match_score`'s token-overlap rule. Normalizing both predicted and expected actions to a canonical vocabulary **before** scoring should lift `action_score` without touching the LLM or retrieval stack.

**Scope (strict eval-side change, not runtime):**

- Build a small canonical action vocabulary as a reviewable file (e.g. `eval/action_vocabulary.json`).
- Build a normalizer (heuristic / keyword / regex first pass) that maps common surface variants → canonical form.
- Apply normalizer inside `_action_match_score` to both sides before token-overlap.
- A/B the scorer behind a flag: raw vs canonicalized, on the existing 40-case held-out artifact (no re-eval of the LLM stack needed for the first pass).

**Boundary — what 7B is explicitly NOT:**

- NOT a retrieval / rerank / query-rewrite / routing change.
- NOT a prompt change.
- NOT a schema change to `MESAnalysisOutput`.
- NOT a change to `eval_cases.json` content (`expected_actions` labels stand verbatim).
- NOT a change to `app.py` or chain construction.

**Dependencies:** None. Can start immediately as a documentation + methodology change.

**Acceptance:** `action_score` lift ≥ +0.020 on the OFF artifact under canonicalized scoring; raw scorer still works (flag-gated); G4 gate continues to PASS.

**Failure mode:** if canonicalized `action_score` lifts < +0.020, the bottleneck is not lexical mismatch — escalate to a different layer (LLM-as-judge scoring, embedding-based action matching, or `expected_actions` label review).

---

## Resume-ready Polish Track (Portfolio Packaging)

**Status:** 🗺 Planned (short-term polish). **Not a research phase.**

This track collects low-effort packaging work whose only purpose is to make the system already on `main` legible to a non-runtime audience — cold email, résumé, and professor / lab outreach. It produces **no new capability**: every item is presentation, reproducibility, or licensing around work that already exists.

**Planned items (each ships as its own separate follow-up PR):**

1. **LICENSE (MIT)** — add a top-level MIT license file so the repo is safe to share publicly.
2. **`baseline_metrics.json`** — commit the G4 baseline as a standalone, human-readable reproducibility artifact for portfolio review. Supports the existing G4 gate; does **not** change G4 logic or thresholds.
3. **`docs/images/ab_results.png`** — render the committed `eval/eval_ab_results.json` A/B numbers as a static chart for README / outreach use.
4. **README metrics table / portfolio framing** — surface the existing eval metrics in a readable table and tighten the top-of-README framing for a reviewer skimming in under a minute.
5. **Architecture diagram refresh** — only if low-effort; refresh the existing diagram to match current phases. Skipped if it would require non-trivial work.

**Boundaries — what this track is NOT:**

- **Not a new research phase.** No new retrieval, reasoning, scoring, or serving capability.
- **Does not replace or reprioritize** the G2 metadata/semantic filter, G4 gate hardening, Phase 7B action canonicalization, or the Phase 7 FastAPI serving work. Those remain the engineering sequence; this track runs alongside as packaging only.
- **Purpose is outreach packaging** — cold email, résumé, professor / lab outreach — not production readiness.
- **Implementation is deferred to separate follow-up PRs**, one per item, none of which touch runtime code, `MESAnalysisOutput` schema, routing, or eval scoring logic.

---

## Dependency-aware execution sequence

This sequence is by **dependency**, not by item recency. New ideas wait for their blockers; no item starts ahead of its measurement floor. The full rationale appears in the IMMEDIATE → LONG-TERM block in `NEXT_STEPS.md`; the per-item dependency annotations live with each item above.

```
IMMEDIATE  → 1. Phase 6.6 closeout (✅ done)
             2. G4 — eval baseline regression gate
             3. G2 — metadata filter
             4. Doc reconciliation (PROJECT_STATE.md, NEXT_STEPS.md)

SHORT-TERM → 5. Backlog #4 — expand benchmark to 100+ cases + inter-rater (20%)
             6. Backlog #2 — embedding model benchmark (under G4 gate)
             7. Backlog #1 — chunking strategy A/B (under G4 gate)

MID-TERM   → 8. Backlog #3 — cross-encoder rerank (consumes G2-filtered candidates)
             9. G3 — LLM-based query rewrite (gated A/B on 100+ benchmark)
            10. G1 — LoRA fine-tune (only after backlog #2 selects a base model)

LONG-TERM  → 11. ENT-1 — Docker (parallel-track, can start any time)
            12. Phase 7 — FastAPI serving
            13. ENT-2 — API auth, ENT-3 — /health + /metrics
            14. Phase 8 — ingestion, Phase 9 — reliability, Backlog #5 — multimodal
```

**Ordering rationale (the four "before" rules):**

- **Phase 6.6 closeout BEFORE any retrieval/embedding tuning.** Without a committed baseline, every later "we improved X by Y points" claim is unfalsifiable.
- **G4 BEFORE the short-term A/B work.** Phase 6.6 produced one baseline; G4 turns it into a gate. Without G4 you trial three changes in parallel and lose attribution.
- **G2 metadata filter BEFORE backlog #3 cross-encoder.** Filter then rank — a cross-encoder on top of unfiltered candidates is doing two jobs and you can't attribute its gains.
- **Backlog #4 BEFORE G3 (LLM rewrite) and G1 (LoRA).** 40 cases are too few to detect realistic 3–5 point deltas; tuning runs on insufficient data are noise.
- **Backlog #2 BEFORE G1 (LoRA).** Fine-tuning the wrong base model is wasted GPU.

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
