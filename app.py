# FINAL CLEAN VERSION (Gemini + OpenAI fallback + safe demo)

import os, time, json, gradio as gr
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

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY","")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY","")
DATA_DIR = os.environ.get("RAG_DATA_DIR","rag_data")

LAST_CALL = 0
def rate_limit():
    global LAST_CALL
    now=time.time()
    if now-LAST_CALL<2:
        raise Exception("⏳ 請間隔2秒")
    LAST_CALL=now

def is_quota(e):
    e=e.lower()
    return "429" in e or "quota" in e or "rate" in e or "resource_exhausted" in e

vectorstore=None
chains={}

def build():
    global vectorstore, chains

    loader=DirectoryLoader(DATA_DIR, glob="**/*.md", loader_cls=TextLoader)
    docs=loader.load()

    splitter=RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits=splitter.split_documents(docs)

    emb=HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    vectorstore=Chroma.from_documents(splits, emb)

    prompt=ChatPromptTemplate.from_messages([
        ("system","你是半導體製程專家，根據知識庫回答"),
        ("human","{question}")
    ])

    if GEMINI_API_KEY:
        llm=ChatGoogleGenerativeAI(model="gemini-2.0-flash",google_api_key=GEMINI_API_KEY)
        retriever=MultiQueryRetriever.from_llm(vectorstore.as_retriever(), llm)
        chains["gemini"]=({"context":retriever| (lambda x:"\n".join([d.page_content for d in x])), "question":RunnablePassthrough()}|prompt|llm|StrOutputParser())

    if OPENAI_API_KEY:
        llm=ChatOpenAI(model="gpt-4o-mini",api_key=OPENAI_API_KEY)
        retriever=MultiQueryRetriever.from_llm(vectorstore.as_retriever(), llm)
        chains["openai"]=({"context":retriever| (lambda x:"\n".join([d.page_content for d in x])), "question":RunnablePassthrough()}|prompt|llm|StrOutputParser())

def chat(msg):
    if len(msg)>300:
        return "請縮短問題"
    rate_limit()

    for p in ["gemini","openai"]:
        if p not in chains: continue
        try:
            r=chains[p].invoke(msg)
            if p=="gemini": return r
            return "[Fallback OpenAI]\n\n"+r
        except Exception as e:
            if p=="gemini" and is_quota(str(e)): continue
            return str(e)

    return "系統錯誤"

def ui():
    with gr.Blocks() as d:
        gr.Markdown("# FAB Copilot RAG (Safe Demo)")
        bot=gr.Chatbot()
        txt=gr.Textbox()

        def run(m,h):
            r=chat(m)
            h.append((m,r))
            return "",h

        txt.submit(run,[txt,bot],[txt,bot])
    return d

if __name__=="__main__":
    build()
    ui().launch()
