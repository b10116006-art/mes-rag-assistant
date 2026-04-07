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

# 半導體製程 FAB Copilot 知識助手

基於 RAG（檢索增強生成）技術的半導體製程知識問答系統。

## 功能

- 💬 **對話助手**：用自然語言詢問製程問題，AI 從知識庫檢索相關資訊回答
- 🔬 **工程分析模式**：輸入異常描述，輸出結構化 JSON 分析結果
- 🔍 **知識庫檢索**：直接搜尋原始知識段落，確認 AI 的參考來源
- ℹ️ **系統說明**：架構介紹與課程對應章節

## 知識庫放置方式

建議將 `.md` 知識庫文件放在 `rag_data/` 目錄下。

例如：
- `rag_data/01_異常類型定義.md`
- `rag_data/02_SOP_異常處置流程.md`
- `rag_data/03_AI_Copilot判斷邏輯.md`
- `rag_data/04_設備常見問題集.md`

## 使用技術

| 技術 | 用途 |
|------|------|
| LangChain | RAG 框架 / LCEL Chain |
| ChromaDB | 向量資料庫 |
| HuggingFace Embeddings | 多語言文字嵌入 |
| Google Gemini 2.0 Flash | LLM 生成回答 |
| Gradio | 網頁介面 |

## 設定

在 Hugging Face Space 的 **Settings → Secrets** 中加入：

- `GEMINI_API_KEY`：你的 Google Gemini API Key

如需更改知識庫資料夾，可額外設定：

- `RAG_DATA_DIR`：知識庫目錄路徑（預設為 `rag_data`）
