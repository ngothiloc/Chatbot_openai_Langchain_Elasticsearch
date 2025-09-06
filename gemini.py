import streamlit as st
import os
import tempfile
import asyncio
from datetime import datetime
import pytz
from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader
)
from langchain_community.document_loaders.unstructured import UnstructuredFileLoader

# -------------------- Cấu hình --------------------
load_dotenv(dotenv_path=".env", override=True)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY không được tìm thấy trong biến môi trường.")

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# -------------------- Elasticsearch --------------------
es = Elasticsearch("http://localhost:9200")
INDEX_NAME = "chatbot"

# Tạo index nếu chưa có
if not es.indices.exists(index=INDEX_NAME):
    es.indices.create(
        index=INDEX_NAME,
        body={
            "mappings": {
                "properties": {
                    "content": {"type": "text"}
                }
            }
        }
    )

# -------------------- Khởi tạo LLM --------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    model_kwargs={"async_client": False},
    google_api_key=GOOGLE_API_KEY
)

# -------------------- Streamlit UI --------------------
st.title("Chatbot AI với Gemini và Elasticsearch")
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
            for doc in documents:
                content = getattr(doc, "page_content", str(doc))
                es.index(index=INDEX_NAME, document={"content": content})

            st.sidebar.success(f"Đã xử lý file: {uploaded_file.name} và lưu vào Elasticsearch")
        except Exception as e:
            st.sidebar.error(f"Lỗi khi xử lý file {uploaded_file.name}: {str(e)}")
        finally:
            os.unlink(tmp_file_path)

# -------------------- Hiển thị document đã lưu --------------------
st.sidebar.subheader("Danh sách document đã lưu trong Elasticsearch")
if st.sidebar.button("Cập nhật danh sách"):
    try:
        res = es.search(index=INDEX_NAME, query={"match_all": {}}, size=1000)
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

    response = ""

    # Kiểm tra câu hỏi về thời gian
    time_keywords = {"date": ["what day", "what date", "today", "ngày", "thứ", "date"],
                     "time": ["what time", "now", "giờ", "thời gian", "time"]}
    
    prompt_lower = prompt.lower()
    is_date = any(k in prompt_lower for k in time_keywords["date"])
    is_time = any(k in prompt_lower for k in time_keywords["time"])

    if is_date or is_time:
        tz = pytz.timezone('Asia/Ho_Chi_Minh')
        now = datetime.now(tz)
        weekdays = ["Thứ Hai","Thứ Ba","Thứ Tư","Thứ Năm","Thứ Sáu","Thứ Bảy","Chủ Nhật"]
        months = [None,"tháng 1","tháng 2","tháng 3","tháng 4","tháng 5","tháng 6",
                  "tháng 7","tháng 8","tháng 9","tháng 10","tháng 11","tháng 12"]

        date_str = f"{weekdays[now.weekday()]}, {now.day} {months[now.month]} năm {now.year}"
        time_str = f"{now.hour:02d}:{now.minute:02d}:{now.second:02d} {tz.zone}"

        if is_date and is_time:
            response = f"Hôm nay là {date_str} và hiện tại là {time_str}"
        elif is_date:
            response = f"Hôm nay là {date_str}"
        else:
            response = f"Bây giờ là {time_str}"

    # Nếu không phải câu hỏi về thời gian, mới gọi LLM + Elasticsearch
    if not response:
        try:
            query = {"query": {"match": {"content": prompt}}}
            res = es.search(index=INDEX_NAME, body=query, size=5)
            context_text = "\n\n".join(hit["_source"]["content"] for hit in res["hits"]["hits"])

            if context_text.strip():
                full_prompt = f"Dữ liệu từ hệ thống: \n{context_text}\n\nHãy trả lời câu hỏi sau dựa trên dữ liệu này:\n{prompt}"
            else:
                full_prompt = f"Hãy trả lời câu hỏi sau: {prompt}"

            llm_response = llm.invoke(full_prompt)
            response = llm_response.content  # Chỉ lấy phần content
        except Exception as e:
            response = f"Tôi xin lỗi, gặp lỗi khi tìm kiếm thông tin: {str(e)}"

    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)

