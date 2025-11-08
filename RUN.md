# 🚀 Hướng dẫn chạy dự án Tool BE

## 📋 Yêu cầu hệ thống

- Python 3.8+
- Redis Server
- PostgreSQL (hoặc SQLite cho development)
- Tesseract OCR (cho xử lý PDF fallback)
- Google Gemini API Key

---

## 🔧 Cài đặt

### 1️⃣ Cài đặt Python dependencies

```bash
pip install -r requirements.txt
```

**Lưu ý:** Nếu dùng Windows, có thể cần:
```bash
python -m pip install -r requirements.txt
```

### 2️⃣ Cài đặt Redis

#### Windows:
- Tải Redis từ: https://github.com/microsoftarchive/redis/releases
- Hoặc dùng Docker: `docker run -d -p 6379:6379 redis:latest`

#### Linux/Mac:
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# MacOS
brew install redis
brew services start redis
```

#### Kiểm tra Redis đã chạy:
```bash
redis-cli ping
# Kết quả: PONG
```

### 3️⃣ Cài đặt PostgreSQL (Tùy chọn)

Nếu dùng PostgreSQL thay vì SQLite:

#### Windows:
- Tải từ: https://www.postgresql.org/download/windows/
- Hoặc dùng Docker: `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16`

#### Linux/Mac:
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# MacOS
brew install postgresql
brew services start postgresql
```

### 4️⃣ Cài đặt Tesseract OCR

#### Windows:
- Tải từ: https://github.com/UB-Mannheim/tesseract/wiki
- Thêm vào PATH: `C:\Program Files\Tesseract-OCR`

#### Linux:
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-vie
```

#### MacOS:
```bash
brew install tesseract tesseract-lang
```

---

## ⚙️ Cấu hình

### 5️⃣ Tạo file `.env`

Tạo file `.env` trong thư mục gốc với nội dung:

```env
# Database
DATABASE_URL=sqlite:///./test.db
# Hoặc PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# JWT Authentication
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Google Gemini API
GEMINI_API_KEY=your-gemini-api-key-here

# Redis (mặc định)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=1
```

**⚠️ Lưu ý:** Thay đổi `SECRET_KEY` và `GEMINI_API_KEY` với giá trị thực tế của bạn!

---

## 🗄️ Database

### 6️⃣ Chạy migrations

```bash
alembic upgrade head
```

Hoặc:
```bash
python -m alembic upgrade head
```

### 7️⃣ Seed dữ liệu (Roles và Users mặc định)

```bash
python -m scripts.seed_roles
```

Hoặc:
```bash
python scripts/seed_roles.py
```

---

## 🏃 Chạy ứng dụng

### 8️⃣ Khởi động Redis

Đảm bảo Redis đang chạy:

```bash
# Kiểm tra Redis
redis-cli ping

# Nếu chưa chạy, khởi động:
# Windows: Chạy redis-server.exe
# Linux: sudo systemctl start redis
# MacOS: brew services start redis
# Docker: docker run -d -p 6379:6379 redis:latest
```

### 9️⃣ Khởi động Celery Worker

Mở terminal mới và chạy:

```bash
# Với eventlet (khuyến nghị cho Windows)
celery -A app.core.celery_app worker -P eventlet --loglevel=info -c 5

# Hoặc với solo (đơn giản hơn, nhưng chậm hơn)
python -m celery -A app.core.celery_app worker -P solo --loglevel=info

# Với gevent (Linux/Mac)
celery -A app.core.celery_app worker -P gevent --loglevel=info -c 5
```

**Lưu ý:** Celery worker cần chạy song song với FastAPI server để xử lý các task bất đồng bộ (như upload ZIP và xử lý PDF).

### 🔟 Khởi động FastAPI Server

Mở terminal mới và chạy:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Hoặc:
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ✅ Kiểm tra

### API Documentation
Truy cập: http://localhost:8000/docs

### Health Check
Truy cập: http://localhost:8000/

### API Endpoints chính:
- **Login:** `POST /api/auth/login`
- **Upload ZIP Reports:** `POST /api/reports/export/{exam_id}/upload-reports`
- **Task Status:** `GET /api/tasks/status/{task_id}`
- **All Tasks:** `GET /api/tasks/status/all`

---

## 🐳 Chạy với Docker (Tùy chọn)

### Sử dụng Docker Compose:

```bash
docker-compose up -d
```

### Build và chạy thủ công:

```bash
# Build image
docker build -t tool_be .

# Chạy container
docker run -d -p 8000:8000 --env-file .env tool_be
```

---

## 🔍 Troubleshooting

### Lỗi: Redis connection failed
- Kiểm tra Redis đã chạy: `redis-cli ping`
- Kiểm tra port 6379 không bị chiếm dụng
- Kiểm tra cấu hình REDIS_HOST trong `.env`

### Lỗi: Celery worker không nhận task
- Đảm bảo Celery worker đang chạy
- Kiểm tra Redis connection
- Kiểm tra log của Celery worker

### Lỗi: Database connection failed
- Kiểm tra DATABASE_URL trong `.env`
- Kiểm tra PostgreSQL/SQLite đã được cài đặt
- Kiểm tra migrations đã chạy: `alembic current`

### Lỗi: Gemini API error
- Kiểm tra GEMINI_API_KEY trong `.env`
- Kiểm tra API key có hợp lệ không
- Kiểm tra quota của Gemini API

### Lỗi: Tesseract not found
- Cài đặt Tesseract OCR
- Thêm Tesseract vào PATH
- Linux: `sudo apt-get install tesseract-ocr tesseract-ocr-vie`

---

## 📝 Tóm tắt lệnh chạy nhanh

```bash
# 1. Cài đặt dependencies
pip install -r requirements.txt

# 2. Tạo file .env (copy từ template trên)

# 3. Chạy migrations
alembic upgrade head

# 4. Seed data
python -m scripts.seed_roles

# 5. Khởi động Redis (terminal 1)
redis-server

# 6. Khởi động Celery Worker (terminal 2)
celery -A app.core.celery_app worker -P eventlet --loglevel=info -c 5

# 7. Khởi động FastAPI Server (terminal 3)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🎯 Lưu ý quan trọng

1. **Celery Worker và FastAPI Server cần chạy song song** - Nếu không có Celery worker, các task xử lý PDF sẽ không chạy.

2. **Redis phải chạy trước** - Celery cần Redis để quản lý tasks.

3. **Google Gemini API Key** - Cần có API key hợp lệ để xử lý PDF.

4. **Tesseract OCR** - Cần cài đặt cho tính năng fallback OCR.

5. **Database** - Có thể dùng SQLite cho development, PostgreSQL cho production.

---

## 📚 Tài liệu thêm

- FastAPI: https://fastapi.tiangolo.com/
- Celery: https://docs.celeryproject.org/
- Redis: https://redis.io/docs/
- Alembic: https://alembic.sqlalchemy.org/

