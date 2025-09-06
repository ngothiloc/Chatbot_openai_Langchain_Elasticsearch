# main.py
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from elasticsearch import Elasticsearch
from langchain.chains import RetrievalQA
from langchain.vectorstores import ElasticsearchStore
# NOTE: use langchain-google-genai integration
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader
)
from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
from dotenv import load_dotenv
from datetime import datetime
import pytz
import os
import tempfile
import google.generativeai as genai

# Load environment variables from .env
load_dotenv()

# Configure Gemini API key (Google Generative AI)
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")  # name in .env
if not GEMINI_API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY in environment or .env file")
genai.configure(api_key=GEMINI_API_KEY)

# Elasticsearch URL (allow override via env)
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
es = Elasticsearch(ES_URL)

# --- LLM (Gemini) via LangChain integration ---
# Use the ChatGoogleGenerativeAI wrapper; model can be "gemini-1.5-flash" or another Gemini family model
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.7)

# --- Embeddings (Gemini/Google) ---
# You can change model to a different embedding model if desired (e.g. "gemini-embedding-001" or Gecko variants)
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

# --- Text splitter (same as before) ---
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

# --- Vectorstore (Elasticsearch) ---
vectorstore = ElasticsearchStore(
    es_connection=es,
    index_name="chatbot",
    embedding=embeddings,
    vector_query_field="embedding"
)

retriever = vectorstore.as_retriever()

# Build RetrievalQA chain using the Gemini LLM
qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# FastAPI app
app = FastAPI(title="Chatbot API (Gemini + LangChain + Elasticsearch)")

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def home():
    return {"status": "Chatbot API (Gemini) is running"}

@app.post("/chatManLab")
def chat(req: ChatRequest):
    prompt = req.message or ""
    prompt_lower = prompt.lower()

    # Kiểm tra câu hỏi về thời gian/ngày (giữ logic cũ)
    time_related_keywords = {
        "date": ["what day", "what date", "today", "ngày", "thứ", "date"],
        "time": ["what time", "now", "giờ", "thời gian", "time"]
    }

    is_date_question = any(k in prompt_lower for k in time_related_keywords["date"])
    is_time_question = any(k in prompt_lower for k in time_related_keywords["time"])

    if is_date_question or is_time_question:
        vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        current_time = datetime.now(vietnam_tz)

        if is_date_question:
            weekday_names = {
                0: "Thứ Hai",
                1: "Thứ Ba",
                2: "Thứ Tư",
                3: "Thứ Năm",
                4: "Thứ Sáu",
                5: "Thứ Bảy",
                6: "Chủ Nhật"
            }
            month_names = {
                1: "tháng 1", 2: "tháng 2", 3: "tháng 3", 4: "tháng 4",
                5: "tháng 5", 6: "tháng 6", 7: "tháng 7", 8: "tháng 8",
                9: "tháng 9", 10: "tháng 10", 11: "tháng 11", 12: "tháng 12"
            }
            response = f"Hôm nay là {weekday_names[current_time.weekday()]}, {current_time.day} {month_names[current_time.month]} năm {current_time.year}"
        else:
            response = f"Bây giờ là {current_time.hour:02d}:{current_time.minute:02d}"
    else:
        try:
            # Use the RetrievalQA chain to answer using indexed docs + Gemini LLM
            response = qa_chain.run(req.message)
        except Exception as e:
            # Return error message but keep API stable
            response = f"Lỗi khi tìm kiếm thông tin / gọi Gemini: {str(e)}"

    return {"answer": response}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(await file.read())
            tmp_path = tmp_file.name

        # Choose loader based on extension
        if file.filename.lower().endswith(".txt"):
            loader = TextLoader(tmp_path)
        elif file.filename.lower().endswith(".pdf"):
            loader = PyPDFLoader(tmp_path)
        elif file.filename.lower().endswith(".docx"):
            loader = UnstructuredFileLoader(tmp_path)
        elif file.filename.lower().endswith(".md"):
            loader = UnstructuredMarkdownLoader(tmp_path)
        else:
            # Clean temp file and return
            os.unlink(tmp_path)
            return {"error": "Unsupported file type"}

        # Load, split and index
        documents = loader.load()
        splits = text_splitter.split_documents(documents)
        vectorstore.add_documents(splits)

        # remove temp file
        os.unlink(tmp_path)
        return {"status": f"Uploaded and indexed {file.filename}"}

    except Exception as e:
        return {"error": str(e)}