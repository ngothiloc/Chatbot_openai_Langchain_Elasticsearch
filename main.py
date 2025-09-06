from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from elasticsearch import Elasticsearch
from langchain.chains import RetrievalQA
from langchain.vectorstores import ElasticsearchStore
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
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

# Load biến môi trường
load_dotenv()

# API key OpenAI
api_key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key

# Kết nối Elasticsearch
es = Elasticsearch("http://elasticsearch:9200")  # trong docker-compose nên dùng tên service

# LLM
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7, max_tokens=100)

# Embeddings
embeddings = OpenAIEmbeddings()

# Text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

# Vectorstore
vectorstore = ElasticsearchStore(
    es_connection=es,
    index_name="chatbot",
    embedding=embeddings,
    vector_query_field="embedding"
)

retriever = vectorstore.as_retriever()
qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# FastAPI app
app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def home():
    return {"status": "Chatbot API is running"}

@app.post("/chatManLab")
def chat(req: ChatRequest):
    prompt = req.message.lower()

    # Kiểm tra câu hỏi về thời gian/ngày
    time_related_keywords = {
        "date": ["what day", "what date", "today", "ngày", "thứ", "date"],
        "time": ["what time", "now", "giờ", "thời gian", "time"]
    }

    is_date_question = any(k in prompt for k in time_related_keywords["date"])
    is_time_question = any(k in prompt for k in time_related_keywords["time"])

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
            response = qa_chain.run(req.message)
        except Exception as e:
            response = f"Lỗi khi tìm kiếm thông tin: {str(e)}"

    return {"answer": response}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(await file.read())
            tmp_path = tmp_file.name

        if file.filename.endswith(".txt"):
            loader = TextLoader(tmp_path)
        elif file.filename.endswith(".pdf"):
            loader = PyPDFLoader(tmp_path)
        elif file.filename.endswith(".docx"):
            loader = UnstructuredFileLoader(tmp_path)
        elif file.filename.endswith(".md"):
            loader = UnstructuredMarkdownLoader(tmp_path)
        else:
            return {"error": "Unsupported file type"}

        documents = loader.load()
        splits = text_splitter.split_documents(documents)
        vectorstore.add_documents(splits)

        os.unlink(tmp_path)
        return {"status": f"Uploaded and indexed {file.filename}"}

    except Exception as e:
        return {"error": str(e)}