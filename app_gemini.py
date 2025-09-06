import streamlit as st
import os
import tempfile
import asyncio
import pickle
from datetime import datetime
import pytz
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError

from langchain.chains import RetrievalQA
from langchain_community.vectorstores import ElasticsearchStore
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader
)
from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# -------------------- Cấu hình --------------------
load_dotenv(dotenv_path=".env", override=True)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY không được tìm thấy trong biến môi trường.")

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Elasticsearch
es = Elasticsearch("http://localhost:9200")
INDEX_NAME = "chatbot"

# Thư mục lưu embeddings cục bộ
EMBEDDING_DIR = "saved_embeddings"
os.makedirs(EMBEDDING_DIR, exist_ok=True)

def get_embedding_path(file_name):
    safe_name = file_name.replace(" ", "_")
    return os.path.join(EMBEDDING_DIR, f"{safe_name}.pkl")

# Tạo index nếu chưa có
if not es.indices.exists(index=INDEX_NAME):
    es.indices.create(
        index=INDEX_NAME,
        body={
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "embedding": {"type": "dense_vector", "dims": 768}
                }
            }
        }
    )

# -------------------- Khởi tạo LLM & Embeddings --------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    # temperature=0.7,
    # max_output_tokens=100,
    model_kwargs={"async_client": False},
    google_api_key=GOOGLE_API_KEY
)

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GOOGLE_API_KEY,
    model_kwargs={"async_client": False}
)

# Text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

# Kết nối ElasticsearchStore
vectorstore = ElasticsearchStore(
    es_connection=es,
    index_name=INDEX_NAME,
    embedding=embeddings,
    vector_query_field="embedding"
)

retriever = vectorstore.as_retriever()
qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# -------------------- Streamlit UI --------------------
st.title("Chatbot AI với Gemini, LangChain và Elasticsearch")
st.sidebar.title("Tải lên tài liệu")

uploaded_files = st.sidebar.file_uploader(
    "Chọn file để tải lên",
    type=['txt', 'pdf', 'docx', 'md'],
    accept_multiple_files=True
)

# -------------------- Xử lý upload file --------------------
if uploaded_files:
    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name

        embedding_path = get_embedding_path(uploaded_file.name)

        try:
            # Load document
            if uploaded_file.name.endswith('.txt'):
                loader = TextLoader(tmp_file_path)
            elif uploaded_file.name.endswith('.pdf'):
                loader = PyPDFLoader(tmp_file_path)
            elif uploaded_file.name.endswith('.docx'):
                loader = UnstructuredFileLoader(tmp_file_path)
            elif uploaded_file.name.endswith('.md'):
                loader = UnstructuredMarkdownLoader(tmp_file_path)

            documents = loader.load()
            splits = text_splitter.split_documents(documents)

            # Nếu embeddings đã lưu, load từ file
            if os.path.exists(embedding_path):
                with open(embedding_path, "rb") as f:
                    saved_docs = pickle.load(f)
                vectorstore.add_documents(saved_docs)
                st.sidebar.success(f"Đã load embeddings từ file: {uploaded_file.name}")
            else:
                # Tạo embeddings mới và lưu
                vectorstore.add_documents(splits)
                with open(embedding_path, "wb") as f:
                    pickle.dump(splits, f)
                st.sidebar.success(f"Đã xử lý file: {uploaded_file.name} và lưu embeddings")
        except Exception as e:
            st.sidebar.error(f"Lỗi khi xử lý file {uploaded_file.name}: {str(e)}")
        finally:
            os.unlink(tmp_file_path)

# -------------------- Hiển thị document đã lưu --------------------
st.sidebar.subheader("Danh sách document đã lưu trong Elasticsearch")

if st.sidebar.button("Cập nhật danh sách"):
    try:
        res = es.search(index=INDEX_NAME, body={"query": {"match_all": {}}}, size=1000)
        docs = [hit["_source"]["content"] for hit in res["hits"]["hits"]]
        st.sidebar.write(f"Tổng số document: {len(docs)}")
        for i, doc in enumerate(docs, 1):
            st.sidebar.write(f"{i}. {doc[:200]}{'...' if len(doc) > 200 else ''}")
    except Exception as e:
        st.sidebar.error(f"Lỗi khi lấy document: {str(e)}")

# -------------------- Chat History --------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# -------------------- Chat Input --------------------
if prompt := st.chat_input("Nhập câu hỏi của bạn"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Kiểm tra câu hỏi về thời gian
    time_keywords = {"date": ["what day", "what date", "today", "ngày", "thứ", "date"],
                     "time": ["what time", "now", "giờ", "thời gian", "time"]}
    
    prompt_lower = prompt.lower()
    is_date = any(k in prompt_lower for k in time_keywords["date"])
    is_time = any(k in prompt_lower for k in time_keywords["time"])

    if is_date or is_time:
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.now(tz)
        if is_date:
            weekdays = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"]
            months = [None,"tháng 1","tháng 2","tháng 3","tháng 4","tháng 5","tháng 6",
                      "tháng 7","tháng 8","tháng 9","tháng 10","tháng 11","tháng 12"]
            response = f"Hôm nay là {weekdays[now.weekday()]}, {now.day} {months[now.month]} năm {now.year}"
        else:
            response = f"Bây giờ là {now.hour:02d}:{now.minute:02d}"
    else:
        try:
            vietnamese_prompt = f"Hãy trả lời bằng tiếng Việt: {prompt}"
            response = qa_chain.run(vietnamese_prompt)
        except Exception as e:
            response = f"Tôi xin lỗi, gặp lỗi khi tìm kiếm thông tin: {str(e)}"

    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)