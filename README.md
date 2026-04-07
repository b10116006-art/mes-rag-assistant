---
title: FAB Copilot MES RAG Assistant
emoji: 🏭
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.1
app_file: app.py
pinned: false
license: mit
---

# 半導體製程 FAB Copilot 知識助手

基於 RAG（檢索增強生成）技術的半導體製程知識問答系統。

## 功能

- 💬 **對話助手**：用自然語言詢問製程問題，AI 從知識庫檢索相關資訊回答
- 🔍 **知識庫檢索**：直接搜尋原始知識段落，確認 AI 的參考來源
- ℹ️ **系統說明**：架構介紹與課程對應章節

## 知識庫涵蓋

1. 製程異常類型定義（ILD、TiN、STI、BPSG、Metal）
2. 標準處置 SOP（設備 OOC、Lot Hold、PM 排程）
3. AI Copilot 判斷邏輯（anomaly_type、risk_level、workflow）
4. 設備故障排除（PECVD、PVD、CMP、Dry Etch）

## 使用技術

| 技術 | 用途 |
|------|------|
| LangChain | RAG 框架 / LCEL Chain |
| ChromaDB | 向量資料庫 |
| HuggingFace Embeddings | 多語言文字嵌入 |
| Google Gemini 2.0 Flash | LLM 生成回答 |
| Gradio | 網頁介面 |

## 設定

在 HuggingFace Space 的 Settings → Secrets 中加入：
- `OPENAI_API_KEY`：你的 OpenAI API Key
