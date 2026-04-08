
"""
半導體製程 FAB Copilot 知識助手
恢復版：保留原本多分頁 UI + 結構化分析 + 知識庫檢索
並加入 Gemini 主模型 + OpenAI fallback + demo 安全保護
"""

import os
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

# ============================================================
# 1. API Key / Config
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
DATA_DIR = os.environ.get("RAG_DATA_DIR", "rag_data")
LAST_CALL_TS = 0

# ============================================================
# 2. 結構化輸出 Schema
# ============================================================
class MESAnalysisOutput(BaseModel):
    anomaly_type: str = Field(description="異常類型代碼")
    risk_level: str = Field(description="HIGH / MEDIUM / LOW")
    confidence: float = Field(description="信心分數 0~1", ge=0.0, le=1.0)
    summary: str = Field(description="異常摘要")
    possible_root_causes: List[str] = Field(description="可能根因列表")
    recommended_actions: List[str] = Field(description="建議處置列表")


# ============================================================
# 3. Global State
# ============================================================
vectorstore = None
chat_chains = {}
analysis_chains = {}


# ============================================================
# 4. Safety / Helpers
# ============================================================
def rate_limit():
    global LAST_CALL_TS
    now = time.time()
    if now - LAST_CALL_TS < 2:
        raise RuntimeError("⏳ 為避免公開 demo 被大量連點，請間隔 2 秒再試。")
    LAST_CALL_TS = now


def is_quota_error(err_text: str) -> bool:
    lowered = err_text.lower()
    return (
        "429" in lowered
        or "quota" in lowered
        or "rate limit" in lowered
        or "resource_exhausted" in lowered
        or "too many requests" in lowered
    )


def make_gemini_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
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


# ============================================================
# 5. Build RAG
# ============================================================
def build_rag_system():
    global vectorstore, chat_chains, analysis_chains

    print("📂 載入知識庫文件...")
    loader = DirectoryLoader(
        DATA_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()

    if not documents and DATA_DIR == "rag_data":
        print("⚠️ rag_data 目錄沒有找到 .md，改從目前目錄尋找知識庫文件...")
        fallback_loader = DirectoryLoader(
            ".",
            glob="*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )
        documents = [
            d for d in fallback_loader.load()
            if not d.metadata.get("source", "").endswith("README.md")
        ]

    if not documents:
        raise RuntimeError("找不到知識庫文件。請建立 rag_data/ 並放入 .md，或設定 RAG_DATA_DIR。")

    print(f"✅ 載入 {len(documents)} 份文件")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n## ", "\n### ", "\n\n", "\n", "。", "，"]
    )
    splits = text_splitter.split_documents(documents)
    print(f"✅ 分割為 {len(splits)} 個 chunks")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={"device": "cpu"}
    )

    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./chroma_db_mes"
    )
    print(f"✅ 向量資料庫建立完成，共 {vectorstore._collection.count()} 筆向量")

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

    print("✅ RAG 系統建立完成，可用 provider:", ", ".join(chat_chains.keys()))
    return True


# ============================================================
# 6. Core Functions
# ============================================================
def chat(message, history):
    if not message.strip():
        return "請輸入問題"
    if len(message) > 300:
        return "⚠️ 請將問題控制在 300 字內，以避免 demo token 消耗過大。"
    if not chat_chains:
        return "⚠️ 尚未設定可用 LLM"

    try:
        rate_limit()
    except Exception as e:
        return str(e)

    providers = []
    if "gemini" in chat_chains:
        providers.append("gemini")
    if "openai" in chat_chains:
        providers.append("openai")

    first_error = None

    for provider in providers:
        try:
            answer = chat_chains[provider].invoke(message)
            if provider == "gemini":
                return answer
            return f"⚠️ Gemini 暫時不可用，已自動切換到 OpenAI gpt-4o-mini\n\n{answer}"
        except Exception as e:
            err_text = str(e)
            if first_error is None:
                first_error = err_text

            if provider == "gemini" and is_quota_error(err_text) and "openai" in chat_chains:
                continue

            if provider == "openai":
                return f"❌ OpenAI fallback 也失敗：{err_text}"

            return f"❌ 錯誤：{err_text}"

    return f"❌ 錯誤：{first_error or '未知錯誤'}"


def analyze_structured(description):
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

    providers = []
    if "gemini" in analysis_chains:
        providers.append("gemini")
    if "openai" in analysis_chains:
        providers.append("openai")

    first_error = None

    for provider in providers:
        try:
            result: MESAnalysisOutput = analysis_chains[provider].invoke(description)
            output = {
                "provider_used": "gemini-2.0-flash" if provider == "gemini" else "gpt-4o-mini",
                "anomaly_type": result.anomaly_type,
                "risk_level": result.risk_level,
                "confidence": result.confidence,
                "summary": result.summary,
                "possible_root_causes": result.possible_root_causes,
                "recommended_actions": result.recommended_actions
            }
            return json.dumps(output, ensure_ascii=False, indent=2)
        except Exception as e:
            err_text = str(e)
            if first_error is None:
                first_error = err_text

            if provider == "gemini" and is_quota_error(err_text) and "openai" in analysis_chains:
                continue

            if provider == "openai":
                return f"❌ OpenAI fallback 也失敗：{err_text}"

            return f"❌ 分析失敗：{err_text}"

    return f"❌ 分析失敗：{first_error or '未知錯誤'}"


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


# ============================================================
# 7. UI
# ============================================================
def create_ui():
    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue="blue"),
        title="FAB Copilot 知識助手"
    ) as demo:

        gr.HTML("""
        <div style="text-align:center; padding:10px">
            <h1>🏭 半導體製程 FAB Copilot 知識助手</h1>
            <p>Multi-Query RAG × 結構化輸出 × ChromaDB × Gemini 主模型 × OpenAI Fallback</p>
        </div>
        """)

        gr.Markdown("""
        ⚠️ 這是公開 demo。  
        預設使用 Gemini；若 quota / rate limit 異常，會自動切到 OpenAI。  
        為避免公開測試造成資源耗盡，系統已加入簡單 rate limit 與輸入長度保護。
        """)

        with gr.Tabs():

            with gr.TabItem("💬 對話助手"):
                gr.Markdown("""
                **使用 Multi-Query RAG**：自動從多角度搜尋知識庫，比單一查詢更準確。

                範例問題：ILD 厚度偏薄怎麼排查？ / TiN 片電阻漂移原因？ / Lot Hold 如何解除？
                """)

                chatbot = gr.Chatbot(
                    height=420,
                    label="FAB Copilot",
                    type="messages"
                )
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="輸入製程問題...",
                        label="",
                        scale=9,
                        container=False
                    )
                    send_btn = gr.Button("送出 ▶", variant="primary", scale=1)

                clear_btn = gr.Button("清除對話", variant="secondary")

                def respond(message, history):
                    if not message.strip():
                        return "", history
                    response = chat(message, history)
                    history.append({"role": "user", "content": message})
                    history.append({"role": "assistant", "content": response})
                    return "", history

                msg_input.submit(respond, [msg_input, chatbot], [msg_input, chatbot])
                send_btn.click(respond, [msg_input, chatbot], [msg_input, chatbot])
                clear_btn.click(lambda: [], outputs=[chatbot])

            with gr.TabItem("🔬 工程分析模式（結構化輸出）"):
                gr.Markdown("""
                **結構化異常分析**：輸入異常描述，輸出與 MES API 相容的 JSON 格式。

                對應欄位：
                `anomaly_type` / `risk_level` / `confidence` / `recommended_actions`

                範例：
                PECVD 腔體壓力飄高 15%，同批次 3 片晶圓粒子計數超標，懷疑腔體問題
                """)

                analysis_input = gr.Textbox(
                    placeholder="描述異常情況，例如：ILD 厚度量測偏薄 8%，49點 map 中心偏低...",
                    label="異常描述",
                    lines=3
                )
                analyze_btn = gr.Button("🔬 執行結構化分析", variant="primary")
                analysis_output = gr.Code(
                    label="結構化輸出（JSON，對應 MES API 格式）",
                    language="json"
                )

                analyze_btn.click(analyze_structured, inputs=analysis_input, outputs=analysis_output)
                analysis_input.submit(analyze_structured, inputs=analysis_input, outputs=analysis_output)

            with gr.TabItem("🔍 知識庫檢索"):
                gr.Markdown("直接查看 AI 回答時參考的原始知識段落。")
                search_input = gr.Textbox(placeholder="輸入關鍵字...", label="搜尋")
                search_btn = gr.Button("搜尋", variant="primary")
                search_output = gr.Markdown()

                search_btn.click(get_relevant_docs, search_input, search_output)
                search_input.submit(get_relevant_docs, search_input, search_output)

            with gr.TabItem("ℹ️ 系統說明"):
                gr.Markdown("""
                ## 課程作業：半導體製程 FAB Copilot 知識助手

                ### 系統架構
                ```
                使用者問題
                    ↓
                Multi-Query Retriever（自動生成多角度查詢）
                    ↓
                ChromaDB 向量資料庫（各角度各取 Top-3，去重合併）
                    ↓
                LangChain LCEL RAG Chain
                    ↓
                Gemini 2.0 Flash（主模型）
                    ↓ quota / rate limit 時 fallback
                OpenAI gpt-4o-mini（備援）
                    ↓
                一般模式：自然語言回答
                工程分析模式：Pydantic 結構化 JSON 輸出
                ```

                ### 技術對應
                - ChromaDB：向量資料庫
                - HuggingFace Embeddings：多語言文字嵌入
                - Multi-Query RAG：提升召回率
                - Pydantic：結構化輸出
                - Gemini + OpenAI fallback：提高 demo 韌性

                ### 與 MES 主專案的銜接關係
                - Multi-Query RAG → Phase B++ retrieval grounding
                - 結構化輸出 → 未來對接 `/overview/ai/action`
                - SOP / troubleshooting → 知識 grounding 層
                """)

        gr.HTML("""
        <div style="text-align:center; margin-top:15px; color:#888; font-size:0.8em;">
            TibaMe LLM 解決方案開發實戰班 課程作業<br>
            LangChain × ChromaDB × Multi-Query RAG × 結構化輸出 × Gemini × OpenAI Fallback × Gradio
        </div>
        """)

    return demo


# ============================================================
# 8. Main
# ============================================================
if __name__ == "__main__":
    print("=" * 55)
    print("🚀 FAB Copilot 知識助手（恢復版 UI + Gemini 主模型 + OpenAI Fallback）")
    print("=" * 55)

    if build_rag_system():
        demo = create_ui()
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False
        )
