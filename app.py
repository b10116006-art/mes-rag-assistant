"""
半導體製程 FAB Copilot 知識助手
Model Switch UI 版：
- 保留原版多分頁 UI
- 保留 Multi-Query RAG
- 支援 UI 切換 Auto / Gemini / OpenAI
- Gemini 自動 retry（503 / 429 / quota-like）
- OpenAI fallback
- provider_used 顯示
"""

import os
import re
import time
import json
import gradio as gr
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

try:
    from langchain_classic.retrievers import MultiQueryRetriever
except ImportError:
    from langchain.retrievers import MultiQueryRetriever

from pydantic import BaseModel, Field
from typing import List

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
DATA_DIR = os.environ.get("RAG_DATA_DIR", "rag_data")
LAST_CALL_TS = 0

class MESAnalysisOutput(BaseModel):
    anomaly_type: str = Field(description="異常類型代碼")
    risk_level: str = Field(description="HIGH / MEDIUM / LOW")
    confidence: float = Field(description="信心分數 0~1", ge=0.0, le=1.0)
    summary: str = Field(description="異常摘要")
    possible_root_causes: List[str] = Field(description="可能根因列表")
    recommended_actions: List[str] = Field(description="建議處置列表")

vectorstore = None
chat_chains = {}
analysis_chains = {}

# --- Memory Layer (Phase 1) ---

MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory", "memory_store.json")
_memory_records: list = []

def load_memory():
    global _memory_records
    if not os.path.exists(MEMORY_FILE):
        print("Memory store not found, skipping:", MEMORY_FILE)
        return
    try:
        with open(MEMORY_FILE, encoding="utf-8") as f:
            _memory_records = json.load(f)
        print(f"Loaded {len(_memory_records)} memory records.")
    except Exception as e:
        print(f"Failed to load memory store: {e}")

def _tokenize(text: str) -> set:
    return set(re.split(r'[\s/_\-,;:.。，、（）【】()]+', text.lower())) - {""}

def retrieve_memory(query: str, top_k: int = 2) -> list:
    if not _memory_records:
        return []
    q_tokens = _tokenize(query)
    scored = []
    for record in _memory_records:
        candidate = " ".join([
            record.get("anomaly_type", ""),
            record.get("layer", ""),
            record.get("machine_id", ""),
            record.get("summary", ""),
            record.get("root_cause", ""),
        ])
        score = len(q_tokens & _tokenize(candidate))
        if score > 0:
            scored.append((score, record))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:top_k]]

def format_memory_context(records: list) -> str:
    if not records:
        return ""
    lines = ["[相關歷史案例]"]
    for r in records:
        lines.append(
            f"- [{r['case_id']}] {r['anomaly_type']} / {r.get('layer', '?')} / {r.get('machine_id', '?')}: "
            f"{r['summary']} | 根因: {r['root_cause']} | 處置: {r['action_taken']} | 結果: {r['outcome']}"
        )
    return "\n".join(lines)

def rate_limit():
    global LAST_CALL_TS
    now = time.time()
    if now - LAST_CALL_TS < 2:
        raise RuntimeError("⏳ 請間隔 2 秒再試。")
    LAST_CALL_TS = now

def is_retryable_gemini_error(err_text: str) -> bool:
    lowered = err_text.lower()
    markers = [
        "503",
        "unavailable",
        "high demand",
        "resource_exhausted",
        "429",
        "quota",
        "rate limit",
        "too many requests",
    ]
    return any(m in lowered for m in markers)

def make_gemini_llm():
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
    )

def make_openai_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key=OPENAI_API_KEY,
        temperature=0.1,
    )

def format_docs(docs):
    seen = set()
    unique_docs = []
    for doc in docs:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique_docs.append(doc)
    return "\n\n---\n\n".join([
        f"【來源：{d.metadata.get('source', '知識庫').split('/')[-1]}】\n{d.page_content}"
        for d in unique_docs
    ])

def build_multi_query_retriever(llm):
    return MultiQueryRetriever.from_llm(
        retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
        llm=llm,
        prompt=PromptTemplate(
            input_variables=["question"],
            template="""你是一個半導體製程專家。
針對以下問題，請從不同角度生成 3 個相關的搜尋查詢，用來從知識庫中找到最相關的資訊。
每行一個查詢，只輸出查詢，不要其他說明。

原始問題：{question}

3 個搜尋查詢："""
        )
    )

def build_rag_system():
    global vectorstore, chat_chains, analysis_chains

    print("DEBUG GEMINI MODEL:", GEMINI_MODEL)
    print("DEBUG GEMINI KEY EXIST:", bool(GEMINI_API_KEY))
    print("DEBUG OPENAI KEY EXIST:", bool(OPENAI_API_KEY))
    load_memory()

    loader = DirectoryLoader(
        DATA_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()

    if not documents and DATA_DIR == "rag_data":
        fallback_loader = DirectoryLoader(
            ".",
            glob="*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )
        documents = [d for d in fallback_loader.load() if not d.metadata.get("source", "").endswith("README.md")]

    if not documents:
        raise RuntimeError("找不到知識庫文件。請建立 rag_data/ 並放入 .md，或設定 RAG_DATA_DIR。")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n## ", "\n### ", "\n\n", "\n", "。", "，"]
    )
    splits = text_splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={"device": "cpu"}
    )

    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./chroma_db_mes"
    )

    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一個半導體製程 FAB Copilot 知識助手。
根據以下知識庫內容回答工程師的問題。

知識庫內容：
{context}

回答規則：
1. 只根據知識庫內容回答，不捏造資訊
2. 使用繁體中文回答
3. 若知識庫找不到相關資訊，請誠實說明
4. 涉及設備操作或安全，請提醒遵循現場 SOP
5. 提供具體數值、步驟和判斷依據"""),
        ("human", "{question}")
    ])

    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一個半導體製程異常分析專家。
根據以下知識庫內容，對工程師描述的異常情況進行結構化分析。

知識庫內容：
{context}

請根據知識庫標準輸出結構化分析結果。
anomaly_type 必須是以下之一：
thickness_ood / particle_count / sheet_resistance / uniformity_fail /
etch_rate_drift / cd_shift / void_detected / general"""),
        ("human", "異常描述：{question}")
    ])

    if GEMINI_API_KEY:
        gemini_llm = make_gemini_llm()
        gemini_retriever = build_multi_query_retriever(gemini_llm)
        chat_chains["gemini"] = (
            {"context": gemini_retriever | format_docs, "question": RunnablePassthrough()}
            | chat_prompt
            | gemini_llm
            | StrOutputParser()
        )
        gemini_structured = gemini_llm.with_structured_output(MESAnalysisOutput)
        analysis_chains["gemini"] = (
            {"context": gemini_retriever | format_docs, "question": RunnablePassthrough()}
            | analysis_prompt
            | gemini_structured
        )

    if OPENAI_API_KEY:
        openai_llm = make_openai_llm()
        openai_retriever = build_multi_query_retriever(openai_llm)
        chat_chains["openai"] = (
            {"context": openai_retriever | format_docs, "question": RunnablePassthrough()}
            | chat_prompt
            | openai_llm
            | StrOutputParser()
        )
        openai_structured = openai_llm.with_structured_output(MESAnalysisOutput)
        analysis_chains["openai"] = (
            {"context": openai_retriever | format_docs, "question": RunnablePassthrough()}
            | analysis_prompt
            | openai_structured
        )

    if not chat_chains:
        raise RuntimeError("尚未設定可用 LLM。請至少提供 GEMINI_API_KEY 或 OPENAI_API_KEY。")

    return True

def test_gemini_health():
    if not GEMINI_API_KEY:
        return "❌ 找不到 GEMINI_API_KEY"
    try:
        llm = make_gemini_llm()
        resp = llm.invoke("請只回覆 OK")
        content = getattr(resp, "content", str(resp))
        return f"✅ Gemini 可用：{GEMINI_MODEL}\n\n模型回覆：{content}"
    except Exception as e:
        return f"⚠️ Gemini 可配置，但目前不可用：{GEMINI_MODEL}\n\n{str(e)}"

def invoke_with_retry(chain, text, provider_name="gemini", retries=1, cooldown=1.2):
    last_err = None
    for attempt in range(retries + 1):
        try:
            return chain.invoke(text)
        except Exception as e:
            last_err = e
            err_text = str(e)
            print(f"{provider_name.upper()} ATTEMPT {attempt+1} ERROR:", err_text)
            if provider_name == "gemini" and is_retryable_gemini_error(err_text) and attempt < retries:
                time.sleep(cooldown)
                continue
            raise last_err
    raise last_err

def run_chat_with_mode(message, mode="auto"):
    if not message.strip():
        return "請輸入問題"
    if len(message) > 300:
        return "⚠️ 請將問題控制在 300 字內。"
    if not chat_chains:
        return "⚠️ 尚未設定可用 LLM"

    try:
        rate_limit()
    except Exception as e:
        return str(e)

    mem_records = retrieve_memory(message)
    mem_block = format_memory_context(mem_records)
    effective_message = f"{mem_block}\n\n{message}" if mem_block else message
    mem_used = len(mem_records) > 0
    mem_ids = [r["case_id"] for r in mem_records]
    _mhdr = f"【memory_used: {'true' if mem_used else 'false'}】"
    if mem_ids:
        _mhdr += f"\n【matched_case_ids: {', '.join(mem_ids)}】"
    _mhdr += "\n"

    if mode == "gemini":
        if "gemini" not in chat_chains:
            return "❌ Gemini 未設定"
        try:
            answer = invoke_with_retry(chat_chains["gemini"], effective_message, provider_name="gemini", retries=1, cooldown=1.2)
            return f"{_mhdr}【provider_used: {GEMINI_MODEL}】\n【mode: gemini】\n\n{answer}"
        except Exception as e:
            return f"❌ Gemini 專用模式失敗：{e}"

    if mode == "openai":
        if "openai" not in chat_chains:
            return "❌ OpenAI 未設定"
        try:
            answer = invoke_with_retry(chat_chains["openai"], effective_message, provider_name="openai", retries=0)
            return f"{_mhdr}【provider_used: gpt-4o-mini】\n【mode: openai】\n\n{answer}"
        except Exception as e:
            return f"❌ OpenAI 專用模式失敗：{e}"

    # auto mode
    if "gemini" in chat_chains:
        try:
            answer = invoke_with_retry(chat_chains["gemini"], effective_message, provider_name="gemini", retries=1, cooldown=1.2)
            return f"{_mhdr}【provider_used: {GEMINI_MODEL}】\n【mode: auto】\n\n{answer}"
        except Exception as e:
            gemini_err = str(e)
            if "openai" in chat_chains and is_retryable_gemini_error(gemini_err):
                try:
                    answer = invoke_with_retry(chat_chains["openai"], effective_message, provider_name="openai", retries=0)
                    return f"{_mhdr}⚠️ Gemini 暫時忙碌或限流，已自動切換到 OpenAI gpt-4o-mini\n【provider_used: openai-fallback】\n【mode: auto】\n\n{answer}"
                except Exception as oe:
                    return f"❌ Gemini 與 OpenAI 都失敗。\nGemini: {gemini_err}\nOpenAI: {oe}"
            return f"❌ Gemini 錯誤：{gemini_err}"

    if "openai" in chat_chains:
        try:
            answer = invoke_with_retry(chat_chains["openai"], effective_message, provider_name="openai", retries=0)
            return f"{_mhdr}【provider_used: openai-only】\n【mode: auto】\n\n{answer}"
        except Exception as oe:
            return f"❌ OpenAI 錯誤：{oe}"

    return "❌ 無可用 provider"

def run_analysis_with_mode(description, mode="auto"):
    if not description.strip():
        return "請描述異常情況"
    if len(description) > 500:
        return "⚠️ 請將異常描述控制在 500 字內。"
    if not analysis_chains:
        return "⚠️ 尚未設定可用 LLM"

    try:
        rate_limit()
    except Exception as e:
        return str(e)

    mem_records = retrieve_memory(description)
    mem_block = format_memory_context(mem_records)
    effective_description = f"{mem_block}\n\n{description}" if mem_block else description
    mem_used = len(mem_records) > 0
    mem_ids = [r["case_id"] for r in mem_records]

    if mode == "gemini":
        if "gemini" not in analysis_chains:
            return "❌ Gemini 未設定"
        try:
            result: MESAnalysisOutput = invoke_with_retry(
                analysis_chains["gemini"], effective_description, provider_name="gemini", retries=1, cooldown=1.2
            )
            output = {
                "provider_used": GEMINI_MODEL,
                "mode": "gemini",
                "anomaly_type": result.anomaly_type,
                "risk_level": result.risk_level,
                "confidence": result.confidence,
                "summary": result.summary,
                "possible_root_causes": result.possible_root_causes,
                "recommended_actions": result.recommended_actions,
                "memory_used": mem_used,
                "matched_case_ids": mem_ids,
            }
            return json.dumps(output, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"❌ Gemini 專用模式分析失敗：{e}"

    if mode == "openai":
        if "openai" not in analysis_chains:
            return "❌ OpenAI 未設定"
        try:
            result: MESAnalysisOutput = invoke_with_retry(
                analysis_chains["openai"], effective_description, provider_name="openai", retries=0
            )
            output = {
                "provider_used": "gpt-4o-mini",
                "mode": "openai",
                "anomaly_type": result.anomaly_type,
                "risk_level": result.risk_level,
                "confidence": result.confidence,
                "summary": result.summary,
                "possible_root_causes": result.possible_root_causes,
                "recommended_actions": result.recommended_actions,
                "memory_used": mem_used,
                "matched_case_ids": mem_ids,
            }
            return json.dumps(output, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"❌ OpenAI 專用模式分析失敗：{e}"

    # auto mode
    if "gemini" in analysis_chains:
        try:
            result: MESAnalysisOutput = invoke_with_retry(
                analysis_chains["gemini"], effective_description, provider_name="gemini", retries=1, cooldown=1.2
            )
            output = {
                "provider_used": GEMINI_MODEL,
                "mode": "auto",
                "anomaly_type": result.anomaly_type,
                "risk_level": result.risk_level,
                "confidence": result.confidence,
                "summary": result.summary,
                "possible_root_causes": result.possible_root_causes,
                "recommended_actions": result.recommended_actions,
                "memory_used": mem_used,
                "matched_case_ids": mem_ids,
            }
            return json.dumps(output, ensure_ascii=False, indent=2)
        except Exception as e:
            gemini_err = str(e)
            if "openai" in analysis_chains and is_retryable_gemini_error(gemini_err):
                try:
                    result: MESAnalysisOutput = invoke_with_retry(
                        analysis_chains["openai"], effective_description, provider_name="openai", retries=0
                    )
                    output = {
                        "provider_used": "openai-fallback",
                        "mode": "auto",
                        "anomaly_type": result.anomaly_type,
                        "risk_level": result.risk_level,
                        "confidence": result.confidence,
                        "summary": result.summary,
                        "possible_root_causes": result.possible_root_causes,
                        "recommended_actions": result.recommended_actions,
                        "fallback_reason": gemini_err,
                        "memory_used": mem_used,
                        "matched_case_ids": mem_ids,
                    }
                    return json.dumps(output, ensure_ascii=False, indent=2)
                except Exception as oe:
                    return f"❌ Gemini 與 OpenAI 都失敗。\nGemini: {gemini_err}\nOpenAI: {oe}"
            return f"❌ Gemini 分析失敗：{gemini_err}"

    if "openai" in analysis_chains:
        try:
            result: MESAnalysisOutput = invoke_with_retry(
                analysis_chains["openai"], effective_description, provider_name="openai", retries=0
            )
            output = {
                "provider_used": "openai-only",
                "mode": "auto",
                "anomaly_type": result.anomaly_type,
                "risk_level": result.risk_level,
                "confidence": result.confidence,
                "summary": result.summary,
                "possible_root_causes": result.possible_root_causes,
                "recommended_actions": result.recommended_actions,
                "memory_used": mem_used,
                "matched_case_ids": mem_ids,
            }
            return json.dumps(output, ensure_ascii=False, indent=2)
        except Exception as oe:
            return f"❌ OpenAI 分析失敗：{oe}"

    return "❌ 無可用 provider"

def get_relevant_docs(query):
    if vectorstore is None:
        return "系統未就緒"
    if not query.strip():
        return "請輸入關鍵字"
    try:
        docs = vectorstore.similarity_search(query, k=3)
        result = "📄 **相關知識庫段落：**\n\n"
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "").split("/")[-1]
            result += f"**[{i}] {source}**\n{doc.page_content[:300]}...\n\n"
        return result
    except Exception as e:
        return f"查詢失敗：{str(e)}"

def create_ui():
    with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue"), title="FAB Copilot 知識助手") as demo:
        gr.HTML("""
        <div style="text-align:center; padding:10px">
            <h1>🏭 半導體製程 FAB Copilot 知識助手</h1>
            <p>Multi-Query RAG × 結構化輸出 × ChromaDB × Gemini 主模型 × OpenAI Fallback</p>
        </div>
        """)
        gr.Markdown(f"公開 demo：預設使用 `{GEMINI_MODEL}`；可在 UI 選擇 Auto / Gemini / OpenAI。")

        with gr.Accordion("🔧 Gemini 健康檢查 / Debug", open=False):
            health_btn = gr.Button("測試 Gemini 是否可用", variant="secondary")
            health_output = gr.Textbox(label="Gemini health check 結果", lines=6)
            health_btn.click(test_gemini_health, outputs=health_output)

        with gr.Tabs():
            with gr.TabItem("💬 對話助手"):
                gr.Markdown("""
                **使用 Multi-Query RAG**：自動從多角度搜尋知識庫，比單一查詢更準確。
                """)
                mode_chat = gr.Radio(
                    choices=["auto", "gemini", "openai"],
                    value="auto",
                    label="對話模式選擇",
                    info="auto=先 Gemini，失敗再 OpenAI；gemini=只用 Gemini；openai=只用 OpenAI"
                )
                chatbot = gr.Chatbot(height=420, label="FAB Copilot", type="messages")
                with gr.Row():
                    msg_input = gr.Textbox(placeholder="輸入製程問題...", label="", scale=9, container=False)
                    send_btn = gr.Button("送出 ▶", variant="primary", scale=1)
                clear_btn = gr.Button("清除對話", variant="secondary")

                def respond(message, history, mode):
                    if not message.strip():
                        return "", history
                    response = run_chat_with_mode(message, mode)
                    history.append({"role": "user", "content": f"[mode={mode}] {message}"})
                    history.append({"role": "assistant", "content": response})
                    return "", history

                msg_input.submit(respond, [msg_input, chatbot, mode_chat], [msg_input, chatbot])
                send_btn.click(respond, [msg_input, chatbot, mode_chat], [msg_input, chatbot])
                clear_btn.click(lambda: [], outputs=[chatbot])

            with gr.TabItem("🔬 工程分析模式（結構化輸出）"):
                mode_analysis = gr.Radio(
                    choices=["auto", "gemini", "openai"],
                    value="auto",
                    label="分析模式選擇",
                    info="auto=先 Gemini，失敗再 OpenAI；gemini=只用 Gemini；openai=只用 OpenAI"
                )
                analysis_input = gr.Textbox(
                    placeholder="描述異常情況，例如：ILD 厚度量測偏薄 8%，49點 map 中心偏低...",
                    label="異常描述",
                    lines=3
                )
                analyze_btn = gr.Button("🔬 執行結構化分析", variant="primary")
                analysis_output = gr.Code(label="結構化輸出（JSON，對應 MES API 格式）", language="json")
                analyze_btn.click(run_analysis_with_mode, inputs=[analysis_input, mode_analysis], outputs=analysis_output)
                analysis_input.submit(run_analysis_with_mode, inputs=[analysis_input, mode_analysis], outputs=analysis_output)

            with gr.TabItem("🔍 知識庫檢索"):
                search_input = gr.Textbox(placeholder="輸入關鍵字...", label="搜尋")
                search_btn = gr.Button("搜尋", variant="primary")
                search_output = gr.Markdown()
                search_btn.click(get_relevant_docs, search_input, search_output)
                search_input.submit(get_relevant_docs, search_input, search_output)

            with gr.TabItem("ℹ️ 系統說明"):
                gr.Markdown(f"""
                ### 目前 Gemini model
                `{GEMINI_MODEL}`

                ### UI 模式
                - `auto`：先 Gemini，503 / 429 / quota-like error 時 retry 後 fallback OpenAI
                - `gemini`：只用 Gemini，方便展示與測試
                - `openai`：只用 OpenAI，方便穩定 demo

                ### 設計目的
                - 保留 Multi-Query RAG
                - 保持原版 UI
                - 提高公開 demo 韌性
                - 讓面試時可以直接展示 provider routing
                """)

    return demo

if __name__ == "__main__":
    print("=" * 55)
    print("🚀 FAB Copilot 知識助手（model switch UI 版）")
    print("=" * 55)
    if build_rag_system():
        demo = create_ui()
        demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
