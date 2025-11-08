# 📤 Hướng dẫn sử dụng trang Upload Báo Cáo

## 🎯 Tính năng

Trang HTML này cho phép bạn:
- ✅ Upload file ZIP chứa các file PDF báo cáo
- ✅ Xem tiến độ upload real-time
- ✅ Theo dõi trạng thái xử lý task
- ✅ Xem kết quả xử lý từng file
- ✅ Xem kết quả kiểm tra đạo văn

---

## 🚀 Cách sử dụng

### Bước 1: Mở file HTML

Mở file `upload_reports.html` trong trình duyệt:
```bash
# Cách 1: Double click vào file
upload_reports.html

# Cách 2: Mở bằng trình duyệt
# Windows
start upload_reports.html

# Mac/Linux
open upload_reports.html
# hoặc
xdg-open upload_reports.html
```

### Bước 2: Đăng nhập để lấy Token

Trước khi upload, bạn cần lấy JWT token từ API đăng nhập:

**POST** `http://localhost:8000/api/auth/login`

**Body:**
```json
{
  "username": "admin",
  "password": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Copy `access_token` và paste vào ô "Access Token" trong form.

### Bước 3: Nhập thông tin

1. **Exam ID**: Nhập ID của kỳ thi (ví dụ: 1, 2, 3...)
2. **Access Token**: Paste token vừa lấy được
3. **File ZIP**: Chọn file ZIP chứa các file PDF báo cáo

### Bước 4: Upload

Click nút **"Upload File"** và chờ:
- Thanh tiến độ sẽ hiển thị % upload
- Sau khi upload thành công, sẽ hiển thị Task ID
- Hệ thống sẽ tự động kiểm tra trạng thái task mỗi 3 giây

### Bước 5: Theo dõi tiến độ

Sau khi upload thành công, bạn sẽ thấy:
- **Trạng thái task**: PENDING, PROCESSING, COMPLETED, FAILED
- **Tiến độ xử lý**: % đã hoàn thành
- **Số file đã xử lý**: Done / Failed / Pending
- **Danh sách file**: Trạng thái từng file
- **Kết quả đạo văn**: Nếu có file bị phát hiện đạo văn

---

## 📋 Yêu cầu file ZIP

### Định dạng:
- File phải có extension `.zip`
- Chỉ chứa các file PDF
- Tối đa 100 file PDF
- Mỗi file tối đa 100MB

### Cấu trúc file ZIP:
```
reports.zip
├── report_001.pdf
├── report_002.pdf
├── report_003.pdf
└── ...
```

---

## 🔍 Kiểm tra trạng thái thủ công

Nếu muốn kiểm tra trạng thái task thủ công, sử dụng API:

**GET** `http://localhost:8000/api/tasks/status/{task_id}`

**Headers:**
```
Authorization: Bearer {your_token}
```

**Response:**
```json
{
  "status": true,
  "task_id": "abc123",
  "task_status": "PROCESSING",
  "progress": 50.5,
  "pdf_total": 10,
  "pdf_done": 5,
  "pdf_failed": 0,
  "pdf_pending": 5,
  "files": [
    {
      "filename": "report_001.pdf",
      "status": "DONE",
      "result": {
        "report_id": 1,
        "student_code": "PH12345",
        "name": "Nguyễn Văn A"
      }
    }
  ],
  "plagiarism_results": [
    {
      "report_id_1": 1,
      "report_id_2": 2,
      "filename_1": "report_001.pdf",
      "filename_2": "report_002.pdf",
      "similarity": 0.85
    }
  ]
}
```

---

## 🐛 Troubleshooting

### Lỗi: "Unauthorized" hoặc 401
- **Nguyên nhân**: Token không hợp lệ hoặc đã hết hạn
- **Giải pháp**: Đăng nhập lại để lấy token mới

### Lỗi: "Exam không tồn tại" hoặc 404
- **Nguyên nhân**: Exam ID không tồn tại trong database
- **Giải pháp**: Kiểm tra lại Exam ID hoặc tạo Exam mới

### Lỗi: "Chỉ chấp nhận file ZIP" hoặc 400
- **Nguyên nhân**: File không phải ZIP hoặc không hợp lệ
- **Giải pháp**: Đảm bảo file có extension `.zip` và không bị hỏng

### Lỗi: "File ZIP không chứa file PDF hợp lệ"
- **Nguyên nhân**: ZIP không có file PDF hoặc chỉ có folder
- **Giải pháp**: Kiểm tra lại file ZIP, đảm bảo có ít nhất 1 file PDF

### Task không xử lý
- **Nguyên nhân**: Celery worker không chạy
- **Giải pháp**: Khởi động Celery worker:
  ```bash
  celery -A app.core.celery_app worker -P eventlet --loglevel=info -c 5
  ```

### Không thấy tiến độ cập nhật
- **Nguyên nhân**: Redis không chạy hoặc Celery worker không kết nối được Redis
- **Giải pháp**: 
  1. Kiểm tra Redis đang chạy: `redis-cli ping`
  2. Khởi động Redis nếu chưa chạy
  3. Kiểm tra cấu hình Redis trong code

---

## 📝 Ghi chú

1. **Token hết hạn**: Token JWT có thời hạn (mặc định 60 phút). Nếu token hết hạn, cần đăng nhập lại.

2. **Auto-refresh**: Trang sẽ tự động kiểm tra trạng thái task mỗi 3 giây. Khi task hoàn thành hoặc thất bại, auto-refresh sẽ dừng.

3. **File lớn**: Với file ZIP lớn (>50MB), quá trình upload có thể mất vài phút. Vui lòng đợi.

4. **Xử lý bất đồng bộ**: Sau khi upload thành công, file sẽ được xử lý bất đồng bộ trong background. Bạn có thể đóng tab và quay lại sau để kiểm tra kết quả.

5. **Kết quả đạo văn**: Hệ thống sẽ tự động kiểm tra đạo văn giữa các file. Nếu phát hiện độ tương đồng >= 80%, 2 file sẽ được đánh dấu là "plagiarized".

---

## 🔗 Liên kết hữu ích

- **API Documentation**: http://localhost:8000/docs
- **Task Status API**: http://localhost:8000/api/tasks/status/{task_id}
- **All Tasks**: http://localhost:8000/api/tasks/status/all

---

## 📞 Hỗ trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra console của trình duyệt (F12)
2. Kiểm tra log của server
3. Kiểm tra log của Celery worker
4. Xem file `RUN.md` để đảm bảo các service đã chạy đúng

