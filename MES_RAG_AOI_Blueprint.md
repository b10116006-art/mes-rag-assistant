# MES × RAG × AOI 三層整合藍圖

## 1. 文件目的
這份文件用來定義我目前三個 AI 相關專案之間的定位與未來整合方式，避免它們被視為彼此無關的小作品。

這三個專案不是三條分裂主線，而是未來同一個 **FAB AI Copilot System** 的不同模組：

- MES 主專案：即時製程監控與 AI decision 主系統
- RAG 專案：知識 grounding 與 SOP / troubleshooting 檢索模組
- AOI 專案：影像缺陷辨識與 visual evidence 模組

---

## 2. 一句話總結
我的整體方向不是做三個獨立 AI app，而是在建立一個可擴展的 **Semiconductor FAB AI Copilot**：

- 用 MES 提供 realtime evidence
- 用 Memory 提供歷史相似案例
- 用 RAG 提供 SOP / OCAP / FMEA 知識 grounding
- 用 AOI 提供 defect image evidence
- 最後交給 LLM 形成可執行的工程決策

---

## 3. 三層模組架構

```text
                ┌────────────────────────────┐
                │     FAB AI Copilot         │
                │     Decision Layer         │
                └────────────┬───────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│ MES / Memory   │  │ RAG Knowledge  │  │ AOI Vision     │
│ Realtime Layer │  │ Grounding Layer│  │ Evidence Layer │
└────────────────┘  └────────────────┘  └────────────────┘
```

---

## 4. Layer 1 — MES 主專案（Core Runtime）

### 4.1 角色
MES 主專案是整個系統的主 runtime，也是目前最成熟的主線。

### 4.2 目前已完成能力
- KPI dashboard
- scrap / yield monitoring
- machine state monitoring
- AI summary
- AI action path
- memory-aware decision
- workflow continuity
- case progression
- trigger gating
- LINE-safe path

### 4.3 這層負責什麼
- 接收即時 scrap / machine state / KPI evidence
- 管理 workflow 與 case lifecycle
- 產生 dashboard / LINE / action output
- 當作未來 AI Copilot 的主入口

### 4.4 目前定位
這層是主系統，不應被 RAG 或 AOI 專案反客為主。

---

## 5. Layer 2 — RAG 專案（Knowledge Grounding Layer）

### 5.1 角色
RAG 專案不是另一個主產品，而是未來 MES 主專案的 **Phase B++ Retrieval Grounding** 驗證模組。

### 5.2 目前已驗證能力
- Multi-Query RAG
- ChromaDB vector retrieval
- HuggingFace multilingual embeddings
- Gemini / OpenAI fallback
- Gradio demo UI
- structured engineering output

### 5.3 這層負責什麼
- 提供 SOP / troubleshooting / anomaly definition / decision logic grounding
- 減少 LLM 純靠語言模型猜測的風險
- 讓 AI 的決策更接近 knowledge-backed engineering assistant

### 5.4 未來如何整回主專案
不是把整個 Gradio app 搬進 MES runtime。

正確方式是：

- 保留主 MES FastAPI runtime
- 將 RAG 檢索結果作為 prompt context 注入
- 優先整到 `/overview/ai/action`
- 採 additive only / minimal diff
- 不改既有 API schema
- 不改 Mongo collections
- 不破壞 Overview / Machines / LINE path

### 5.5 RAG 未來知識來源
- SOP
- OCAP
- FMEA
- 歷史異常處理案例
- 製程 troubleshooting 文件
- equipment FAQ

---

## 6. Layer 3 — AOI 專案（Vision Evidence Layer）

### 6.1 角色
AOI 專案未來不是獨立與 MES 平行運作，而是作為 **visual evidence provider**。

### 6.2 這層負責什麼
- defect detection
- defect classification
- image-based anomaly recognition
- 視覺證據轉為結構化 evidence

### 6.3 未來輸出格式（建議）
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

### 6.4 AOI 不應直接做的事
- 不應自己當主 decision system
- 不應直接接管 MES workflow
- 不應一開始就與主 runtime 緊耦合

AOI 應先輸出標準化 evidence，再交由 Copilot decision layer 使用。

---

## 7. 三層如何整合

### 7.1 最終資料流
```text
Realtime MES Data
(scrap / machine state / KPI)
        ↓
Memory Layer
(similar historical cases)
        ↓
RAG Layer
(SOP / troubleshooting / OCAP knowledge)
        ↓
AOI Layer
(defect image evidence)
        ↓
LLM Decision Layer
(summary / root cause / action)
        ↓
Dashboard / Action Panel / LINE / Workflow
```

### 7.2 Prompt 組合概念
```text
[Realtime Evidence]
- layer
- machine
- scrap / KPI / machine_state

[Memory]
- similar case history
- prior workflow context

[RAG Knowledge]
- SOP
- troubleshooting
- anomaly definition
- OCAP hints

[AOI Evidence]
- defect_type
- confidence
- image clue
- location

[Task]
請輸出結構化分析與建議行動
```

---

## 8. 整合順序（非常重要）

### 現在
- 作業先獨立提交
- RAG 專案先維持獨立可 demo
- 主 MES runtime 先不直接併入 Gradio app
- AOI 專案先不硬接主系統

### 下一步
- 將 RAG 以 prompt injection 方式整進 MES `/overview/ai/action`
- 先只接 retrieval grounding
- 保持 minimal diff

### 再下一步
- AOI 先輸出標準 evidence schema
- 再讓 Copilot 把 AOI 視為另一種 evidence source
- 最後才考慮更深的 workflow linkage

---

## 9. 設計原則

### 9.1 Modular first
先模組化驗證，再整合，不要一開始全部硬揉在一起。

### 9.2 Additive only
每一步優先 additive change，不破壞既有主 runtime。

### 9.3 Main runtime stays in MES
MES 專案仍然是主系統；RAG 與 AOI 都是能力模組，不是主體替代品。

### 9.4 Evidence before action
AI action 應建立在：
- realtime evidence
- memory evidence
- knowledge evidence
- visual evidence

而不是只靠單次 LLM 回答。

---

## 10. 面試敘事版本
我目前不是做三個彼此無關的 AI 專案，而是在建立一個可擴展的半導體 FAB AI Copilot 架構。

其中：
- MES 主專案負責 realtime monitoring、workflow、decision path
- RAG 專案負責 SOP / troubleshooting grounding
- AOI 專案負責 defect image evidence

我刻意先把高風險能力拆成獨立模組驗證，確認效果後，再以 minimal-diff 方式整合回主系統。這樣做的好處是：

- 降低主 runtime 風險
- 保持系統可 demo、可驗證、可擴展
- 對後續面試與專案敘事更有結構

---

## 11. 結論
最終我要做的不是三個分裂專案，而是一個由多模組構成的 **FAB AI Copilot System**。

- MES 是主 runtime
- RAG 是 knowledge grounding layer
- AOI 是 visual evidence layer
- LLM 是 decision layer

這樣的架構能逐步演進成真正的工程輔助系統，而不是只停留在單點 AI demo。
