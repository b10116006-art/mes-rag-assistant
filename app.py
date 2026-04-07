"""
半導體製程 FAB Copilot 知識助手
MES RAG Assistant - TibaMe LLM 解決方案開發實戰班 課程作業

技術棧：
- LangChain LCEL (課程 7.02)
- Multi-Query RAG 進階檢索 (課程 7.05)
- 結構化輸出 Pydantic (課程 7.03)
- ChromaDB 向量資料庫 (課程 4.03)
- HuggingFace Embeddings 多語言嵌入 (課程 4.02)
- Google Gemini LLM (課程 1.03)
- Gradio 介面
"""

import os
import json
import gradio as gr
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain.retrievers import MultiQueryRetriever
from pydantic import BaseModel, Field
from typing import List, Optional

# ============================================================
# 1. API Key 設定
# ============================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ============================================================
# 2. 結構化輸出 Schema（對應課程 7.03，對應 MES Phase B 格式）
# ============================================================
class MESAnalysisOutput(BaseModel):
    """半導體製程異常分析結構化輸出，對應 MES AI Copilot 的回應格式"""
    anomaly_type: str = Field(
        description="異常類型代碼，例如：thickness_ood / particle_count / sheet_resistance / etch_rate_drift / general"
    )
    risk_level: str = Field(
        description="風險等級：HIGH / MEDIUM / LOW"
    )
    confidence: float = Field(
        description="信心分數，0.0 到 1.0",
        ge=0.0, le=1.0
    )
    summary: str = Field(
        description="異常摘要，50字以內"
    )
    possible_root_causes: List[str] = Field(
        description="可能的根本原因列表，最多3項"
    )
    recommended_actions: List[str] = Field(
        description="建議的處置行動列表，最多3項"
    )

# ============================================================
# 3. 全域變數（只初始化一次）
# ============================================================
vectorstore = None
rag_chain = None          # 一般對話 RAG chain
analysis_chain = None     # 結構化輸出 chain（工程分析模式）

# ============================================================
# 4. 建立 RAG 系統
# ============================================================
def build_rag_system():
    global vectorstore, rag_chain, analysis_chain

    print("📂 載入知識庫文件...")
    loader = DirectoryLoader(
        "rag_data",
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    documents = loader.load()
    print(f"  ✅ 載入 {len(documents)} 份文件")

    # 文本分段（Parent-Document 概念：保留較大 chunk 給 context）
    print("✂️  文本分段中...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=80,
        separators=["\n## ", "\n### ", "\n\n", "\n", "。", "，"]
    )
    splits = text_splitter.split_documents(documents)
    print(f"  ✅ 分割為 {len(splits)} 個 chunk")

    # 多語言 Embedding 模型
    print("🔢 載入 Embedding 模型（首次需要下載）...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={"device": "cpu"}
    )

    # ChromaDB 向量資料庫
    print("🗄️  建立 ChromaDB 向量資料庫...")
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./chroma_db_mes"
    )
    print(f"  ✅ 向量資料庫建立完成，共 {vectorstore._collection.count()} 筆向量")

    # LLM 設定
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.1,
    )

    # ── Multi-Query Retriever（課程 7.05 進階技術）──────────────
    # 自動從不同角度生成多個查詢，提升召回率
    multi_query_retriever = MultiQueryRetriever.from_llm(
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

    # ── 一般對話 RAG Chain（LCEL 語法，課程 7.02）──────────────
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

    rag_chain = (
        {"context": multi_query_retriever | format_docs, "question": RunnablePassthrough()}
        | chat_prompt
        | llm
        | StrOutputParser()
    )

    # ── 結構化輸出 Chain（課程 7.03，對應 MES Phase B 格式）──────
    analysis_prompt = ChatPromptTemplate.from_messages([
        ("system", """你是一個半導體製程異常分析專家。
根據以下知識庫內容，對工程師描述的異常情況進行結構化分析。

知識庫內容：
{context}

請根據知識庫的標準，輸出結構化的異常分析結果。
anomaly_type 必須是以下之一：
thickness_ood / particle_count / sheet_resistance / uniformity_fail /
etch_rate_drift / cd_shift / void_detected / general"""),
        ("human", "異常描述：{question}")
    ])

    llm_structured = llm.with_structured_output(MESAnalysisOutput)

    analysis_chain = (
        {"context": multi_query_retriever | format_docs, "question": RunnablePassthrough()}
        | analysis_prompt
        | llm_structured
    )

    print("✅ RAG 系統（Multi-Query + 結構化輸出）建立完成！")
    return True


# ============================================================
# 5. 對話函數
# ============================================================
def chat(message, history):
    if not GEMINI_API_KEY:
        return "⚠️ 請先設定 GEMINI_API_KEY 環境變數"
    if rag_chain is None:
        return "⚠️ RAG 系統尚未初始化，請稍候"
    if not message.strip():
        return "請輸入問題"
    try:
        return rag_chain.invoke(message)
    except Exception as e:
        return f"❌ 錯誤：{str(e)}"


def analyze_structured(description):
    """結構化異常分析（對應 MES Phase B 格式）"""
    if not GEMINI_API_KEY:
        return "⚠️ 請先設定 GEMINI_API_KEY"
    if analysis_chain is None:
        return "⚠️ 系統尚未初始化"
    if not description.strip():
        return "請描述異常情況"
    try:
        result: MESAnalysisOutput = analysis_chain.invoke(description)
        # 輸出 JSON（對應 MES API response 格式）
        output = {
            "anomaly_type": result.anomaly_type,
            "risk_level": result.risk_level,
            "confidence": result.confidence,
            "summary": result.summary,
            "possible_root_causes": result.possible_root_causes,
            "recommended_actions": result.recommended_actions
        }
        return json.dumps(output, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"❌ 分析失敗：{str(e)}"


def get_relevant_docs(query):
    if vectorstore is None:
        return "系統未就緒"
    try:
        docs = vectorstore.similarity_search(query, k=3)
        result = "📄 **相關知識庫段落：**\n\n"
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', '').split('/')[-1]
            result += f"**[{i}] {source}**\n{doc.page_content[:300]}...\n\n"
        return result
    except Exception as e:
        return f"查詢失敗：{str(e)}"


# ============================================================
# 6. Gradio 介面
# ============================================================
def create_ui():
    with gr.Blocks(
        theme=gr.themes.Soft(primary_hue="blue"),
        title="FAB Copilot 知識助手"
    ) as demo:

        gr.HTML("""
        <div style="text-align:center; padding:10px">
            <h1>🏭 半導體製程 FAB Copilot 知識助手</h1>
            <p>Multi-Query RAG × 結構化輸出 × ChromaDB × Google Gemini</p>
        </div>
        """)

        with gr.Tabs():

            # ── Tab 1：對話助手（Multi-Query RAG）──────────────
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
                        label="", scale=9, container=False
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

            # ── Tab 2：工程分析模式（結構化輸出）──────────────
            with gr.TabItem("🔬 工程分析模式（結構化輸出）"):
                gr.Markdown("""
                **結構化異常分析**：輸入異常描述，輸出與 MES API 相容的 JSON 格式。

                對應課程 7.03 結構化輸出，輸出格式與 MES `/overview/ai/action` 相容：
                `anomaly_type` / `risk_level` / `confidence` / `recommended_actions`

                **範例**：PECVD 腔體壓力飄高 15%，同批次3片晶圓粒子計數超標，懷疑腔體問題
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

            # ── Tab 3：知識庫檢索 ──────────────────────────────
            with gr.TabItem("🔍 知識庫檢索"):
                gr.Markdown("直接查看 AI 回答時參考的原始知識段落。")
                search_input = gr.Textbox(placeholder="輸入關鍵字...", label="搜尋")
                search_btn = gr.Button("搜尋", variant="primary")
                search_output = gr.Markdown()
                search_btn.click(get_relevant_docs, search_input, search_output)
                search_input.submit(get_relevant_docs, search_input, search_output)

            # ── Tab 4：系統說明 ────────────────────────────────
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
                Google Gemini 2.0 Flash
                    ↓
                一般模式：自然語言回答
                工程分析模式：Pydantic 結構化 JSON 輸出
                ```

                ### 技術對應課程章節
                | 技術 | 課程章節 |
                |------|---------|
                | ChromaDB 向量資料庫 | 4.03 向量資料庫 |
                | HuggingFace Embeddings | 4.02 文字嵌入模型 |
                | LCEL Chain 架構 | 7.02 LCEL |
                | Multi-Query RAG | 7.05 RAG進階 |
                | 結構化輸出 Pydantic | 7.03 結構化輸出 |
                | Google Gemini API | 1.03 雲端模型串接 |
                | Agentic 設計概念 | 8.05 Agentic RAG |

                ### 與 MES 主專案的銜接關係
                | 本作業元件 | MES 對應模組 |
                |-----------|------------|
                | Multi-Query RAG | Phase B++ retrieval grounding |
                | 結構化輸出 JSON | Phase B parse_llm_structured_output() 強化版 |
                | ChromaDB + Embeddings | SOP / OCAP 知識庫 |
                | Gemini LLM | 與 MES 共用同一 provider |

                ### 知識庫涵蓋範圍
                1. 製程異常類型定義（ILD / TiN / STI / BPSG / Metal）
                2. 標準處置 SOP（設備 OOC、Lot Hold、PM 排程）
                3. AI Copilot 判斷邏輯（anomaly_type、risk_level、workflow）
                4. 設備故障排除（PECVD / PVD / CMP / Dry Etch）
                """)

        gr.HTML("""
        <div style="text-align:center; margin-top:15px; color:#888; font-size:0.8em;">
            TibaMe LLM 解決方案開發實戰班 課程作業<br>
            LangChain × ChromaDB × Multi-Query RAG × 結構化輸出 × Google Gemini × Gradio
        </div>
        """)

    return demo


# ============================================================
# 7. 主程式
# ============================================================
if __name__ == "__main__":
    print("=" * 55)
    print("🚀 FAB Copilot 知識助手（Multi-Query + 結構化輸出）")
    print("=" * 55)

    if build_rag_system():
        demo = create_ui()
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False
        )
