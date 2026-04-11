# Changelog

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
