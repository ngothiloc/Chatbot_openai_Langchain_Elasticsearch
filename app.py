import streamlit as st
import os
from src.services.elasticsearch_service import ElasticsearchService
from src.handlers.chat_handler import ChatHandler

# Khởi tạo các service
es_service = ElasticsearchService()
chat_handler = ChatHandler(es_service.get_retriever())

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
        success, message = es_service.process_file(uploaded_file)
        if success:
            st.sidebar.success(message)
        else:
            st.sidebar.error(message)

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

    # Get response from chat handler
    response = chat_handler.handle_query(prompt)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)

