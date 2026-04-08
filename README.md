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
- 💬 對話助手
- 🔬 工程分析模式
- 🔍 知識庫檢索
- ℹ️ 系統說明
- 🔁 Gemini 主模型 + OpenAI fallback

## 設定
在 Hugging Face Space 的 Settings → Secrets 中加入：
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`

可選：
- `RAG_DATA_DIR`（預設為 `rag_data`）
