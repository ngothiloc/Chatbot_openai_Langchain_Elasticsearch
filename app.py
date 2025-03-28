import streamlit as st
import os
from elasticsearch import Elasticsearch
from langchain.chains import RetrievalQA
from langchain.vectorstores import ElasticsearchStore
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from datetime import datetime
import pytz
from dotenv import load_dotenv
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader
)
from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tempfile


# Load biến môi trường từ file .env
load_dotenv()

# Thiết lập API key cho OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY không được tìm thấy trong biến môi trường. Vui lòng kiểm tra file .env")
os.environ["OPENAI_API_KEY"] = api_key

# Kết nối Elasticsearch
es = Elasticsearch("http://localhost:9200")

# Khởi tạo mô hình gpt-4o-mini từ OpenAI
llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.7, max_tokens=100) # Điều chỉnh temperature nếu cần

# Khởi tạo bộ tạo embedding bằng OpenAI
embeddings = OpenAIEmbeddings()

# Khởi tạo text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)

# Kết nối với ElasticsearchStore
vectorstore = ElasticsearchStore(
    es_connection=es,
    index_name="chatbot",
    embedding=embeddings,
    vector_query_field="embedding"
)

# Tạo retriever từ vectorstore
retriever = vectorstore.as_retriever()

# Tạo RetrievalQA chain
qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# Giao diện Streamlit
st.title("Chatbot AI với OpenAI, LangChain và Elasticsearch")

# File uploader
st.sidebar.title("Tải lên tài liệu")
uploaded_files = st.sidebar.file_uploader(
    "Chọn file để tải lên",
    type=['txt', 'pdf', 'docx', 'md'],
    accept_multiple_files=True
)

# Process uploaded files
if uploaded_files:
    for uploaded_file in uploaded_files:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name

        try:
            # Load document based on file type
            if uploaded_file.name.endswith('.txt'):
                loader = TextLoader(tmp_file_path)
            elif uploaded_file.name.endswith('.pdf'):
                loader = PyPDFLoader(tmp_file_path)
            elif uploaded_file.name.endswith('.docx'):
                loader = UnstructuredFileLoader(tmp_file_path)
            elif uploaded_file.name.endswith('.md'):
                loader = UnstructuredMarkdownLoader(tmp_file_path)
            
            # Load and split the document
            documents = loader.load()
            splits = text_splitter.split_documents(documents)
            
            # Add documents to vectorstore
            vectorstore.add_documents(splits)
            st.sidebar.success(f"Đã xử lý thành công file: {uploaded_file.name}")
            
        except Exception as e:
            st.sidebar.error(f"Lỗi khi xử lý file {uploaded_file.name}: {str(e)}")
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Nhập câu hỏi của bạn"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Check if it's a time-related question
    time_related_keywords = {
        "date": ["what day", "what date", "today", "ngày", "thứ", "date"],
        "time": ["what time", "now", "giờ", "thời gian", "time"]
    }
    
    prompt_lower = prompt.lower()
    is_date_question = any(keyword in prompt_lower for keyword in time_related_keywords["date"])
    is_time_question = any(keyword in prompt_lower for keyword in time_related_keywords["time"])

    if is_date_question or is_time_question:
        vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        current_time = datetime.now(vietnam_tz)
        
        if is_date_question:
            # Format date in Vietnamese
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
                1: "tháng 1",
                2: "tháng 2",
                3: "tháng 3",
                4: "tháng 4",
                5: "tháng 5",
                6: "tháng 6",
                7: "tháng 7",
                8: "tháng 8",
                9: "tháng 9",
                10: "tháng 10",
                11: "tháng 11",
                12: "tháng 12"
            }
            response = f"Hôm nay là {weekday_names[current_time.weekday()]}, {current_time.day} {month_names[current_time.month]} năm {current_time.year}"
        else:
            # Format time in Vietnamese
            response = f"Bây giờ là {current_time.hour:02d}:{current_time.minute:02d}"
    else:
        # Use Elasticsearch for specific queries
        try:
            response = qa_chain.run(prompt)
        except Exception as e:
            response = f"Tôi xin lỗi, nhưng tôi gặp lỗi khi tìm kiếm thông tin: {str(e)}"

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)

