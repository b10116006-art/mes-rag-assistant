# FAB AI Copilot — Claude / ChatGPT 可讀版本

## System Identity
This is not three unrelated projects.

It is one evolving system with three major modules:

1. MES Core Runtime
2. RAG Knowledge Grounding Module
3. AOI Vision Evidence Module

The final target is a modular **FAB AI Copilot System**.

---

## 1. MES Core Runtime
Role:
- Primary runtime system
- Owns workflow, dashboard, memory, trigger, action path

Current responsibility:
- realtime KPI / scrap / machine state
- AI summary / AI action
- workflow continuity
- trigger gating
- LINE-safe path

Important rule:
- MES remains the main runtime
- RAG and AOI should not replace the MES core

---

## 2. RAG Knowledge Module
Role:
- Knowledge grounding layer
- Provides SOP / troubleshooting / anomaly definitions / OCAP hints

Current status:
- Independent prototype already validated
- Multi-Query RAG
- ChromaDB
- multilingual embeddings
- Gemini / OpenAI fallback
- Gradio demo

Future integration rule:
- Do NOT move the whole Gradio app into MES
- Inject retrieved RAG context into MES prompt construction
- First target path: `/overview/ai/action`
- Keep additive only / minimal diff
- Do not break API schema or Mongo collections

---

## 3. AOI Vision Module
Role:
- Visual evidence layer
- Provides image-based defect detection / classification output

Expected output style:
```json
{
  "defect_type": "particle",
  "confidence": 0.92,
  "location": "center_cluster",
  "image_id": "img_001",
  "machine_id": "PECVD-01",
  "layer": "ILD",
  "ts": "2026-04-08T10:20:00"
}
```

Integration rule:
- AOI should first become a structured evidence provider
- AOI should not directly own MES workflow
- AOI should feed the copilot decision layer

---

## 4. Unified Decision Flow
```text
Realtime MES evidence
→ memory evidence
→ RAG knowledge evidence
→ AOI visual evidence
→ LLM decision layer
→ dashboard / action / LINE / workflow
```

---

## 5. Prompt Composition Concept
```text
[Realtime Evidence]
Current machine / KPI / scrap / state

[Memory]
Similar historical anomaly cases

[RAG Knowledge]
SOP / troubleshooting / anomaly definitions / OCAP hints

[AOI Evidence]
Visual defect classification results

[Task]
Generate structured engineering analysis and actions
```

---

## 6. Integration Order
Now:
- keep homework RAG project independent
- keep MES runtime stable
- do not hard-merge AOI yet

Next:
- integrate RAG into MES prompt path as grounding context
- prioritize `/overview/ai/action`

Later:
- standardize AOI output schema
- feed AOI output into copilot as an evidence source
- then evaluate deeper workflow linkage

---

## 7. Design Principles
- modular first
- additive only
- minimal diff
- MES remains main runtime
- evidence before action
- avoid hard coupling too early

---

## 8. One-Sentence Positioning
This is not a collection of separate demos.

It is a staged architecture for a semiconductor **FAB AI Copilot**, where:
- MES is the runtime core
- RAG is the knowledge grounding layer
- AOI is the visual evidence layer
- LLM is the decision layer
