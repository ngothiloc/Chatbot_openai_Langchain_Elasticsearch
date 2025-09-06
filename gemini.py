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
st.title("🤖 Chatbot AI với Gemini & Elasticsearch")
st.sidebar.title("📂 Tải lên tài liệu")

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

            st.sidebar.success(f"✅ Đã xử lý file: {uploaded_file.name} và lưu vào Elasticsearch")
        except Exception as e:
            st.sidebar.error(f"❌ Lỗi khi xử lý file {uploaded_file.name}: {str(e)}")
        finally:
            os.unlink(tmp_file_path)

# -------------------- Hiển thị document đã lưu --------------------
st.sidebar.subheader("📑 Danh sách document đã lưu trong Elasticsearch")
if st.sidebar.button("Cập nhật danh sách"):
    try:
        res = es.search(index=INDEX_NAME, query={"match_all": {}}, size=1000)
        docs = [hit["_source"]["content"] for hit in res["hits"]["hits"]]
        st.sidebar.write(f"🔎 Tổng số document: {len(docs)}")
        for i, doc in enumerate(docs, 1):
            st.sidebar.write(f"{i}. {doc[:200]}{'...' if len(doc) > 200 else ''}")
    except Exception as e:
        st.sidebar.error(f"❌ Lỗi khi lấy document: {str(e)}")

# -------------------- Chat History --------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# -------------------- Chat Response --------------------
import random

greetings = [
    "Theo mình biết thì...",
    "Hello 👋, theo thông tin mình biết được...",
    "Chào bạn 👋, mình biết rằng...",
    "Xin chào, theo kiến thức mình có thì...",
    "Hi bạn 😃, mình được biết rằng...",
    "Theo những gì mình biết thì...",
    "Chào bạn, mình biết được thông tin như sau...",
    "Theo hiểu biết của mình thì...",
    "Hello bạn, mình có thể chia sẻ rằng...",
    "Theo kiến thức mình biết thì..."
]


closings = [
    "Hy vọng thông tin này hữu ích cho bạn 😊",
    "Mong rằng câu trả lời đã giúp bạn 👍",
    "Nếu cần thêm chi tiết, mình sẵn sàng hỗ trợ nhé 🌟"
    "Rất vui khi được hỗ trợ!"
]

greeting = random.choice(greetings)
closing = random.choice(closings)

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
            response = f"📅 Hôm nay là {date_str} và ⏰ hiện tại là {time_str}"
        elif is_date:
            response = f"📅 Hôm nay là {date_str}"
        else:
            response = f"⏰ Bây giờ là {time_str}"

    # Nếu không phải câu hỏi về thời gian, mới gọi LLM + Elasticsearch
    if not response:
        try:
            query = {"query": {"match": {"content": prompt}}}
            res = es.search(index=INDEX_NAME, body=query, size=5)
            context_text = "\n\n".join(hit["_source"]["content"] for hit in res["hits"]["hits"])

            if context_text.strip():
                full_prompt = f"""
ạn là một trợ lý AI thân thiện, nói chuyện tự nhiên và dễ hiểu. 
Vai trò của bạn gồm:

1. Trả lời câu hỏi của người dùng dựa trên dữ liệu cung cấp (ưu tiên sử dụng dữ liệu này khi có liên quan).
2. Ngoài dữ liệu cung cấp, bạn cũng có thể chia sẻ các kiến thức cơ bản về:
   - Cuộc sống hàng ngày (ví dụ: thời gian, thời tiết, thói quen, sức khỏe cơ bản...).
   - Các đất nước, con người, văn hóa, lịch sử.
   - Việt Nam: văn hóa, địa lý, lịch sử, các sự kiện cơ bản
   - Các quốc gia khác: văn hóa, địa lý, lịch sử, các sự kiện cơ bản.
   - Các môn học, ngành nghề, công việc.
   - Các vấn đề xã hội, chính trị, xã hội.
3. Khi không tìm thấy câu trả lời trong dữ liệu, hãy dùng kiến thức chung để trả lời thay vì nói "không biết".

Phong cách trả lời:
- Luôn có lời chào ngắn gọn ở đầu (nhưng thay đổi cách chào, ví dụ: "Chào bạn 👋", "Xin chào", "Hi bạn 😃").
- Nội dung trả lời ngắn gọn, dễ hiểu, có thể dùng gạch đầu dòng.
- Luôn có câu kết thúc lịch sự ở cuối (thay đổi linh hoạt, ví dụ: "Hy vọng thông tin này hữu ích 😊", "Mong rằng điều này giúp ích cho bạn 👍").
- Sau câu kết thúc, gợi ý thêm 2-3 câu hỏi tiếp theo (đa dạng kiểu: "Tại sao...", "Làm thế nào...", "Bao lâu...", "Ở đâu...").

4 Về ETV – Viện Kiểm định Công nghệ và Môi trường: 
   * Là một viện chuyên cung cấp các dịch vụ: kiểm định, hiệu chuẩn, quan trắc môi trường, quan trắc đối chứng, thiết kế cơ sở dữ liệu và phần mềm quản lý. 
   * Có đội ngũ chuyên gia giàu kinh nghiệm và năng lực trong nghiên cứu và ứng dụng công nghệ mới. 
   * Có hồ sơ năng lực, gồm: quyết định chỉ định kiểm định/ hiệu chuẩn/ thử nghiệm (mới nhất năm 2024), công nhận ISO 17025, danh mục quy trình & phương tiện đo.
   * Trụ sở tại Khu C3-2B/NO4, phường Thạch Bàn, Quận Long Biên, Hà Nội, và có cam kết bảo mật thông tin người dùng.

Khi người dùng hỏi về ETV, bạn có thể trả lời dựa trên thông tin này.

Dữ liệu:
{context_text}

Yêu cầu trả lời:
- Bắt đầu câu trả lời bằng: "{greeting}"
- Trả lời ngắn gọn, súc tích, có thể dùng gạch đầu dòng nếu nhiều ý.
- Kết thúc bằng: "{closing}"
- Sau câu kết thúc, hãy gợi ý 2-3 câu hỏi liên quan mà người dùng có thể hỏi tiếp theo.
- Tuyệt đối không lặp lại nguyên văn toàn bộ dữ liệu, chỉ chọn thông tin liên quan.

Câu hỏi: {prompt}
"""
            else:
                full_prompt = f"Bạn hãy trả lời ngắn gọn, thân thiện và dễ hiểu cho câu hỏi: {prompt}"

            llm_response = llm.invoke(full_prompt)
            response = llm_response.content  # Chỉ lấy phần content
        except Exception as e:
            response = f"⚠️ Tôi xin lỗi, gặp lỗi khi tìm kiếm thông tin: {str(e)}"

    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)
