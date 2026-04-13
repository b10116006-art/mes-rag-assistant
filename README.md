---
title: FAB Copilot MES RAG Assistant
emoji: 🏭
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 5.23.3
app_file: app.py
pinned: false
license: mit
---

# MES RAG Assistant — FAB Copilot Knowledge & Decision Core

## Purpose

This repo is the **RAG / LLM decision brain** for the FAB AI Copilot system.
It handles knowledge retrieval, LLM reasoning, structured output, and evaluation.
It does **not** run MES pipelines, dashboards, or AOI vision training.

## What this repo does today

- Multi-Query RAG over semiconductor process knowledge documents (`rag_data/`)
- Gemini primary / OpenAI fallback provider routing with automatic retry
- Structured engineering analysis output (`MESAnalysisOutput` via Pydantic)
- Gradio demo UI for local testing and interview demos
- ChromaDB vector store with multilingual HuggingFace embeddings

## What belongs in this repo

| In scope | Description |
|---|---|
| RAG retrieval | Document chunking, vector store, multi-query |
| LLM reasoning | Chat and structured analysis chains |
| Memory-based retrieval | Historical event context injection (Phase 1) |
| Structured output | Pydantic-validated JSON decision schema |
| Evaluation | Retrieval and decision quality metrics (Phase 4) |
| Provider routing | Gemini / OpenAI failover, future cloud providers |
| Cloud-ready serving | FastAPI serving layer (Phase 7) |

## What does NOT belong in this repo

- AOI / computer vision training or inference
- MES MQTT ingestion or real-time data pipeline
- MES dashboard backend or frontend
- Machine utilization business logic
- LINE notification delivery

## Local run

```bash
pip install -r requirements.txt

export GEMINI_API_KEY=your_key      # required
export OPENAI_API_KEY=your_key      # optional fallback

python app.py
# → http://localhost:7860
```

Add knowledge documents as `.md` files to `rag_data/` before running.

## Local evaluation (Phase 4)

A small offline evaluation harness lives under `eval/`. It runs a labeled case set through the analysis path and reports decision / routing / memory accuracy — no API endpoints, no dashboards.

```bash
python eval/run_eval.py
```

- Cases: `eval/eval_cases.json` (10 labeled queries)
- Results: `eval/eval_results.json` (full per-case detail)
- Memory and routing metrics work even without API keys; `anomaly_type_accuracy` requires a live LLM

## HF Secrets (Hugging Face Space)

- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_MODEL` (optional, default: `gemini-2.5-flash`)

## Roadmap summary

| Phase | Focus |
|---|---|
| 0 | Repo foundation (current) |
| 1 | Memory-based RAG |
| 2 | Structured Decision Output |
| 3 | Context Orchestrator |
| 4 | Evaluation Layer |
| 5 | Decision Engine |
| 6 | Reliability / Provider Routing |
| 7 | Cloud-ready Deployment |
| 8 | Document Normalization |

See [AI_ROADMAP.md](AI_ROADMAP.md) for full phase details.


User / MES / AOI
      ↓
RAG retrieval (docs + memory)
      ↓
Context assembly
      ↓
LLM reasoning
      ↓
Structured output
      ↓
Return to MES / UI