# 🐛 Hướng dẫn Debug - Tìm và sửa lỗi

## 🔍 Các lỗi thường gặp và cách khắc phục

### 1. Lỗi CORS (Cross-Origin Resource Sharing)

**Triệu chứng:**
```
Access to XMLHttpRequest at 'http://localhost:8000/api/...' from origin 'file://' has been blocked by CORS policy
```

**Nguyên nhân:**
- Mở file HTML trực tiếp từ file system (file://)
- Server chưa cấu hình CORS

**Giải pháp:**
1. **Chạy file HTML qua HTTP server:**
   ```bash
   # Cách 1: Dùng Python
   python -m http.server 8080
   # Sau đó truy cập: http://localhost:8080/upload_reports.html
   
   # Cách 2: Dùng Node.js
   npx http-server -p 8080
   
   # Cách 3: Dùng VS Code Live Server extension
   ```

2. **Kiểm tra CORS trong FastAPI:**
   Đảm bảo file `app/main.py` có cấu hình CORS:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Hoặc chỉ định origin cụ thể
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

---

### 2. Lỗi 401 Unauthorized

**Triệu chứng:**
```
401 Unauthorized
{"detail": "Not authenticated"}
```

**Nguyên nhân:**
- Token không hợp lệ hoặc đã hết hạn
- Token không được gửi đúng format

**Giải pháp:**
1. **Kiểm tra token:**
   - Mở `login.html` và đăng nhập lại
   - Copy token mới
   - Paste vào form upload

2. **Kiểm tra format token trong request:**
   - Mở Developer Tools (F12)
   - Tab Network → Xem request headers
   - Đảm bảo header có: `Authorization: Bearer {token}`

3. **Kiểm tra token có hợp lệ:**
   ```bash
   # Test token với curl
   curl -X GET "http://localhost:8000/api/reports" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

---

### 3. Lỗi 404 Not Found

**Triệu chứng:**
```
404 Not Found
{"detail": "Not Found"}
```

**Nguyên nhân:**
- Endpoint không tồn tại
- Đường dẫn API sai
- Router chưa được đăng ký

**Giải pháp:**
1. **Kiểm tra endpoint:**
   - Mở http://localhost:8000/docs
   - Tìm endpoint `/api/reports/{exam_id}/upload-reports`
   - Kiểm tra method: POST

2. **Kiểm tra router:**
   Đảm bảo trong `app/api/routes/api.py` có:
   ```python
   router.include_router(report_router.router)
   ```

3. **Kiểm tra prefix:**
   - Router có prefix: `/reports`
   - API base: `/api`
   - Endpoint: `/{exam_id}/upload-reports`
   - **Đường dẫn đầy đủ:** `/api/reports/{exam_id}/upload-reports`

---

### 4. Lỗi 500 Internal Server Error

**Triệu chứng:**
```
500 Internal Server Error
```

**Nguyên nhân:**
- Lỗi trong code Python
- Database connection failed
- Celery không chạy
- Redis không chạy

**Giải pháp:**
1. **Kiểm tra log server:**
   ```bash
   # Xem log trong terminal chạy uvicorn
   # Tìm dòng có "ERROR" hoặc "Traceback"
   ```

2. **Kiểm tra các service:**
   ```bash
   # Redis
   redis-cli ping
   # Kết quả: PONG
   
   # Celery
   # Kiểm tra terminal chạy Celery worker
   # Đảm bảo không có lỗi
   ```

3. **Kiểm tra database:**
   ```bash
   # SQLite
   ls -la test.db
   
   # PostgreSQL
   psql -U postgres -d app -c "SELECT 1;"
   ```

4. **Kiểm tra file upload folder:**
   ```bash
   # Đảm bảo folder tồn tại và có quyền ghi
   mkdir -p uploads/reports
   chmod 755 uploads/reports
   ```

---

### 5. Lỗi "File ZIP không hợp lệ"

**Triệu chứng:**
```
400 Bad Request
{"detail": "File ZIP không hợp lệ"}
```

**Nguyên nhân:**
- File không phải ZIP
- File ZIP bị hỏng
- File quá lớn

**Giải pháp:**
1. **Kiểm tra file:**
   - Mở file ZIP bằng WinRAR/7-Zip
   - Đảm bảo file không bị hỏng
   - Thử giải nén thủ công

2. **Kiểm tra kích thước:**
   - Giới hạn: 100MB/file
   - Tối đa 100 file trong ZIP

3. **Kiểm tra format:**
   - Chỉ chứa file PDF
   - Không có folder trong ZIP

---

### 6. Lỗi "Celery task không chạy"

**Triệu chứng:**
- Upload thành công nhưng task không xử lý
- Task status luôn là PENDING

**Nguyên nhân:**
- Celery worker không chạy
- Redis không kết nối được
- Task bị lỗi

**Giải pháp:**
1. **Kiểm tra Celery worker:**
   ```bash
   # Đảm bảo Celery worker đang chạy
   celery -A app.core.celery_app worker -P eventlet --loglevel=info -c 5
   ```

2. **Kiểm tra Redis:**
   ```bash
   redis-cli ping
   # Kết quả: PONG
   ```

3. **Kiểm tra log Celery:**
   - Xem terminal chạy Celery worker
   - Tìm lỗi hoặc warning

4. **Test Celery:**
   ```python
   # Trong Python shell
   from app.core.celery_app import celery_app
   result = celery_app.control.inspect().active()
   print(result)
   ```

---

### 7. Lỗi "Exam không tồn tại"

**Triệu chứng:**
```
404 Not Found
{"detail": "Kỳ thi không tồn tại"}
```

**Nguyên nhân:**
- Exam ID không tồn tại trong database

**Giải pháp:**
1. **Kiểm tra Exam trong database:**
   ```bash
   # SQLite
   sqlite3 test.db "SELECT id, name, code FROM exams;"
   
   # PostgreSQL
   psql -U postgres -d app -c "SELECT id, name, code FROM exams;"
   ```

2. **Tạo Exam mới:**
   - Sử dụng API: POST `/api/exams`
   - Hoặc dùng admin panel

---

### 8. Lỗi "Token không hợp lệ"

**Triệu chứng:**
```
401 Unauthorized
{"detail": "Could not validate credentials"}
```

**Nguyên nhân:**
- Token đã hết hạn
- Token không đúng format
- SECRET_KEY không khớp

**Giải pháp:**
1. **Kiểm tra token expiration:**
   - Mặc định: 60 phút
   - Đăng nhập lại để lấy token mới

2. **Kiểm tra SECRET_KEY:**
   - Đảm bảo SECRET_KEY trong `.env` không đổi
   - Nếu đổi SECRET_KEY, cần đăng nhập lại

---

## 🔧 Công cụ Debug

### 1. Browser Developer Tools (F12)

**Console Tab:**
- Xem JavaScript errors
- Xem log messages
- Test API calls

**Network Tab:**
- Xem HTTP requests/responses
- Kiểm tra headers
- Xem response body

**Application Tab:**
- Xem localStorage
- Xem cookies
- Clear storage

### 2. Server Logs

**FastAPI Server:**
```bash
# Xem log trong terminal chạy uvicorn
# Tìm các dòng có ERROR, WARNING
```

**Celery Worker:**
```bash
# Xem log trong terminal chạy Celery
# Tìm các dòng có ERROR, WARNING
```

### 3. API Testing Tools

**Postman:**
- Test API endpoints
- Kiểm tra authentication
- Xem response format

**curl:**
```bash
# Test login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"123456"}'

# Test upload (với token)
curl -X POST "http://localhost:8000/api/reports/1/upload-reports" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.zip"
```

---

## 📝 Checklist Debug

Khi gặp lỗi, kiểm tra theo thứ tự:

- [ ] **Server đã chạy chưa?**
  ```bash
  curl http://localhost:8000/
  ```

- [ ] **Redis đã chạy chưa?**
  ```bash
  redis-cli ping
  ```

- [ ] **Celery worker đã chạy chưa?**
  - Kiểm tra terminal chạy Celery

- [ ] **Database đã được migrate chưa?**
  ```bash
  alembic current
  ```

- [ ] **Token có hợp lệ không?**
  - Đăng nhập lại và lấy token mới

- [ ] **File ZIP có hợp lệ không?**
  - Thử mở bằng WinRAR/7-Zip

- [ ] **CORS đã được cấu hình chưa?**
  - Kiểm tra `app/main.py`

- [ ] **Endpoint có đúng không?**
  - Kiểm tra http://localhost:8000/docs

- [ ] **Log có lỗi gì không?**
  - Xem terminal chạy server và Celery

---

## 🆘 Liên hệ hỗ trợ

Nếu vẫn gặp lỗi:

1. **Thu thập thông tin:**
   - Screenshot lỗi
   - Log từ server
   - Log từ browser console
   - Request/Response từ Network tab

2. **Kiểm tra lại:**
   - Đọc file `RUN.md`
   - Đọc file `UPLOAD_GUIDE.md`
   - Kiểm tra các file cấu hình

3. **Tạo issue:**
   - Mô tả lỗi chi tiết
   - Các bước để reproduce
   - Thông tin môi trường (OS, Python version, etc.)

---

## 🎯 Quick Fix Commands

```bash
# Restart tất cả services
# Terminal 1: Redis
redis-server

# Terminal 2: Celery
celery -A app.core.celery_app worker -P eventlet --loglevel=info -c 5

# Terminal 3: FastAPI
uvicorn app.main:app --reload

# Clear Redis (nếu cần)
redis-cli FLUSHDB

# Clear database (nếu cần)
alembic downgrade base
alembic upgrade head
python -m scripts.seed_roles
```

