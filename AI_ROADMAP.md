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

## Phase 4: Evaluation Layer

**Objective:** Add automated quality metrics for retrieval relevance and decision accuracy.

**Why it matters:** Without evaluation, there is no signal for whether improvements are real or regressions are introduced.

**Acceptance criteria:**
- Retrieval evaluation: top-k recall against a labeled test set
- Decision evaluation: structured output accuracy on sample anomaly cases
- Evaluation script runnable independently

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
