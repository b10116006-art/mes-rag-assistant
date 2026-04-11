# Architecture — RAG / LLM Decision Core

## Role of this repo

This repo is the **knowledge retrieval and LLM decision brain** of the FAB AI Copilot system.

It is not a runtime system. It does not own dashboards, data pipelines, or notification delivery.
Its job is: given a question or anomaly description, retrieve relevant knowledge, reason over it, and return a structured engineering decision.

---

## Current components

```
app.py
 ├── RAG pipeline (LangChain + ChromaDB)
 │    ├── DirectoryLoader → rag_data/*.md
 │    ├── RecursiveCharacterTextSplitter
 │    ├── HuggingFaceEmbeddings (multilingual)
 │    └── Chroma vectorstore (./chroma_db_mes)
 ├── Multi-Query Retriever (per-provider LLM)
 ├── Chat chain (freeform Q&A)
 ├── Analysis chain (structured output → MESAnalysisOutput)
 ├── Provider routing (Gemini primary / OpenAI fallback)
 └── Gradio demo UI
```

---

## Inputs this repo expects

| Input | Format | Source |
|---|---|---|
| Knowledge documents | `.md` files in `rag_data/` | Manually curated SOP / FAQ / OCAP / FMEA |
| User query | Plain text string | Gradio UI or future API caller |
| Anomaly description | Plain text string | Engineer or future MES runtime |
| Memory events (Phase 1) | Structured records | Future: MES memory store |
| AOI evidence (future) | JSON evidence object | Future: AOI project output |

---

## Outputs this repo produces

| Output | Format | Consumer |
|---|---|---|
| Chat answer | Markdown string | Engineer via Gradio UI |
| Structured analysis | `MESAnalysisOutput` JSON | Future: MES runtime API |
| Retrieved doc chunks | Text + source metadata | Internal / debug |

---

## Future integration: AOI project

The AOI project produces visual defect evidence:
```json
{
  "defect_type": "particle",
  "confidence": 0.92,
  "location": "center_cluster",
  "machine_id": "PECVD-01",
  "layer": "ILD"
}
```

This repo will consume AOI output as an **additional evidence input** to the analysis prompt.
AOI does not call into this repo. This repo receives AOI evidence and includes it in context assembly.

Integration point: Phase 3 (Context Orchestrator) or Phase 5 (Decision Engine).

---

## Future integration: AI MES project

The MES project is the primary runtime system. It owns:
- Realtime KPI / scrap / machine state
- Workflow lifecycle and trigger gating
- Dashboard and LINE notification delivery

This repo does **not** replace or duplicate MES runtime.

Integration path (Phase 7):
- This repo exposes a FastAPI `/analyze` endpoint
- MES runtime calls `/analyze` to get RAG-grounded structured decisions
- MES injects the result into its action path (`/overview/ai/action`)
- No MES schema or collection is modified by this repo

---

## Integration boundary rule

This repo produces decisions. Other systems act on them.
This repo never writes to MES databases, sends LINE messages, or controls machine parameters directly.
