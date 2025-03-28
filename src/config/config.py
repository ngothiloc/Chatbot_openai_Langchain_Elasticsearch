import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Cấu hình OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY không được tìm thấy trong biến môi trường. Vui lòng kiểm tra file .env")

# Cấu hình Elasticsearch
ELASTICSEARCH_URL = "http://localhost:9200"

# Cấu hình model
MODEL_NAME = "gpt-4o-mini"
TEMPERATURE = 0.7
MAX_TOKENS = 100

# Cấu hình text splitter
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
SEPARATORS = ["\n\n", "\n", " ", ""]

# Cấu hình timezone
TIMEZONE = 'Asia/Ho_Chi_Minh'

# Cấu hình từ khóa thời gian
TIME_RELATED_KEYWORDS = {
    "date": ["what day", "what date", "today", "ngày", "thứ", "date"],
    "time": ["what time", "now", "giờ", "thời gian", "time"]
}

# Cấu hình tên ngày và tháng
WEEKDAY_NAMES = {
    0: "Thứ Hai",
    1: "Thứ Ba",
    2: "Thứ Tư",
    3: "Thứ Năm",
    4: "Thứ Sáu",
    5: "Thứ Bảy",
    6: "Chủ Nhật"
}

MONTH_NAMES = {
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