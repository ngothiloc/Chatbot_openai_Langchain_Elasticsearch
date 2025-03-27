# Chatbot AI với OpenAI, LangChain và Elasticsearch

Ứng dụng chatbot thông minh có khả năng đọc và học từ tài liệu, trả lời câu hỏi về thời gian và tìm kiếm thông tin từ tài liệu đã được tải lên.

## Yêu cầu hệ thống

- Python 3.9 trở lên
- Docker và Docker Compose
- API key của OpenAI

## Cài đặt các thư viện cần thiết

```bash
# Cài đặt các thư viện chính
pip3 install streamlit
pip3 install elasticsearch
pip3 install langchain
pip3 install langchain-community
pip3 install openai
pip3 install python-dotenv
pip3 install pytz

# Cài đặt các thư viện xử lý tài liệu
pip3 install unstructured[all-docs]
pip3 install python-docx
pip3 install pypdf
pip3 install pdf2image
pip3 install python-magic
pip3 install nltk
pip3 install beautifulsoup4
```

## Cấu hình và Chạy Elasticsearch

1. Đảm bảo Docker và Docker Compose đã được cài đặt trên máy của bạn

2. Chạy Elasticsearch bằng Docker Compose:

```bash
# Khởi động Elasticsearch
docker-compose up -d

# Kiểm tra trạng thái
docker-compose ps

# Kiểm tra Elasticsearch đang chạy
curl http://localhost:9200
```

3. Nếu gặp lỗi về quyền truy cập, chạy lệnh sau:

```bash
sudo chown -R 1000:1000 elasticsearch-data
```

4. Dừng Elasticsearch khi cần:

```bash
docker-compose down
```

## Cấu hình

1. **Cấu hình biến môi trường**:

   - Copy file `.env.example` thành `.env`:

   ```bash
   cp .env.example .env
   ```

   - Mở file `.env` và cập nhật API key của OpenAI:

   ```
   OPENAI_API_KEY=your-api-key-here
   ```

2. **Kiểm tra cấu hình**:
   - Đảm bảo file `.env` đã được tạo và có API key hợp lệ
   - Chạy ứng dụng để kiểm tra:
   ```bash
   streamlit run app.py
   ```

## Chạy ứng dụng

1. Khởi động ứng dụng Streamlit:

```bash
streamlit run app.py
```

2. Mở trình duyệt web và truy cập địa chỉ được hiển thị (thường là http://localhost:8501)

## Cấu trúc thư mục

```
.
├── app.py                 # File chính của ứng dụng
├── docker-compose.yml     # Cấu hình Docker cho Elasticsearch
├── elasticsearch-data/    # Thư mục lưu dữ liệu Elasticsearch
└── README.md             # Tài liệu hướng dẫn
```

## Tính năng

1. **Tải lên tài liệu**:

   - Hỗ trợ các định dạng: .txt, .pdf, .docx, .md
   - Tự động xử lý và lưu trữ nội dung vào Elasticsearch

2. **Trả lời câu hỏi về thời gian**:

   - Hỏi về ngày hiện tại
   - Hỏi về giờ hiện tại
   - Hỗ trợ cả tiếng Việt và tiếng Anh

3. **Tìm kiếm thông tin từ tài liệu**:
   - Trả lời câu hỏi dựa trên nội dung tài liệu đã tải lên
   - Sử dụng Elasticsearch để tìm kiếm thông tin

## Cách sử dụng

1. **Tải lên tài liệu**:

   - Sử dụng phần "Tải lên tài liệu" ở sidebar
   - Chọn một hoặc nhiều file để tải lên
   - Đợi quá trình xử lý hoàn tất

2. **Đặt câu hỏi**:
   - Nhập câu hỏi vào ô chat
   - Chatbot sẽ trả lời dựa trên:
     - Thông tin thời gian (nếu là câu hỏi về ngày/giờ)
     - Nội dung tài liệu đã tải lên (nếu là câu hỏi về thông tin)

## Xử lý lỗi thường gặp

1. **Elasticsearch không kết nối được**:

   - Kiểm tra Docker daemon đang chạy
   - Chạy lại lệnh `docker-compose up -d`
   - Kiểm tra logs: `docker-compose logs elasticsearch`

2. **Lỗi quyền truy cập Elasticsearch**:

   - Chạy lệnh: `sudo chown -R 1000:1000 elasticsearch-data`
   - Khởi động lại Elasticsearch: `docker-compose restart`

3. **Lỗi khi tải lên file**:
   - Kiểm tra định dạng file có được hỗ trợ không
   - Đảm bảo file không bị hỏng
   - Thử tải lên từng file một

## Quản lý dữ liệu Elasticsearch trong Docker

1. **Xem danh sách volumes**:

```bash
docker volume ls
```

2. **Xem thông tin chi tiết volume**:

```bash
docker volume inspect elasticsearch-data
```

3. **Xem dữ liệu trong container**:

```bash
# Truy cập vào container
docker exec -it elasticsearch /bin/bash

# Xem dữ liệu trong thư mục data
ls -la /usr/share/elasticsearch/data
```

4. **Xóa và khởi động lại dữ liệu**:

```bash
# Dừng container
docker-compose down

# Xóa volume
docker volume rm elasticsearch-data

# Khởi động lại
docker-compose up -d
```

5. **Kiểm tra trạng thái Elasticsearch**:

```bash
# Xem logs
docker-compose logs elasticsearch

# Kiểm tra API
curl http://localhost:9200/_cat/indices
```

## Kiểm tra dữ liệu trong Elasticsearch

1. **Xem danh sách indices**:

```bash
curl http://localhost:9200/_cat/indices
```

2. **Xem dữ liệu trong index chatbot**:

```bash
curl http://localhost:9200/chatbot/_search?pretty
```

3. **Xem cấu trúc của index**:

```bash
curl http://localhost:9200/chatbot/_mapping?pretty
```

4. **Xóa index chatbot** (nếu cần):

```bash
curl -X DELETE http://localhost:9200/chatbot
```

## Backup và Restore dữ liệu

### Backup dữ liệu (trên máy cũ)

1. **Tạo snapshot repository**:

```bash
curl -X PUT "http://localhost:9200/_snapshot/my_backup" -H 'Content-Type: application/json' -d '{
  "type": "fs",
  "settings": {
    "location": "/usr/share/elasticsearch/data/backup"
  }
}'
```

2. **Tạo snapshot**:

```bash
curl -X PUT "http://localhost:9200/_snapshot/my_backup/snapshot_1?wait_for_completion=true"
```

3. **Copy thư mục backup**:

```bash
# Copy từ container ra máy host
docker cp elasticsearch:/usr/share/elasticsearch/data/backup ./elasticsearch-backup
```

### Restore dữ liệu (trên máy mới)

1. **Copy thư mục backup vào container**:

```bash
# Copy từ máy host vào container
docker cp ./elasticsearch-backup elasticsearch:/usr/share/elasticsearch/data/backup
```

2. **Restore snapshot**:

```bash
curl -X POST "http://localhost:9200/_snapshot/my_backup/snapshot_1/_restore?wait_for_completion=true"
```

### Lưu ý khi chuyển máy

- Dữ liệu Elasticsearch được lưu local trên mỗi máy
- Khi chạy trên máy mới, cần backup và restore dữ liệu hoặc train lại
- Có thể sử dụng Elasticsearch Cloud để lưu trữ dữ liệu tập trung
- Nên lưu lại các file tài liệu gốc để có thể train lại khi cần

## Lưu ý

- Đảm bảo Elasticsearch đang chạy trước khi khởi động ứng dụng
- API key của OpenAI phải hợp lệ
- Kích thước file tải lên không nên quá lớn
- Nên tải lên từng file một để dễ theo dõi quá trình xử lý
- Dữ liệu được lưu trữ trong Elasticsearch thông qua API endpoint http://localhost:9200
- Để xem dữ liệu đã lưu, sử dụng lệnh: `curl http://localhost:9200/chatbot/_search?pretty`
- Để xóa dữ liệu, sử dụng lệnh: `curl -X DELETE http://localhost:9200/chatbot`
- Docker volume `elasticsearch-data` chỉ là nơi Elasticsearch lưu trữ dữ liệu của nó
