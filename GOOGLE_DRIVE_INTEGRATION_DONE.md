# 🚀 Upload trực tiếp lên Google Drive - Hoàn thành!

## 📝 Thay đổi được thực hiện

### 1. **`app/services/report_service.py`**
   - Cập nhật hàm `process_zip_upload()` để upload trực tiếp lên Google Drive
   - Khi `GOOGLE_DRIVE_ENABLED=true`: Tạo folder trên Google Drive + upload từng file PDF
   - Khi `GOOGLE_DRIVE_ENABLED=false`: Fallback về local storage
   - File được lưu với `path_storage=gdrive://file_id` (Google Drive) hoặc `path_storage=/local/path` (Local)

### 2. **`app/tasks/report_tasks.py`**
   - Cập nhật `process_uploaded_archive()` để xử lý file từ cả Google Drive và Local
   - Khi `path_storage` bắt đầu với `gdrive://`, tự động download từ Google Drive
   - Khi `path_storage` là path, đọc từ Local Storage

### 3. **`app/core/config.py`**
   - Thêm biến cấu hình: `GOOGLE_DRIVE_ENABLED`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_DRIVE_ROOT_FOLDER_ID`

### 4. **`.env`**
   - Enable Google Drive: `GOOGLE_DRIVE_ENABLED=true`
   - Cấu hình các biến môi trường

---

## ⚙️ Cách cấu hình

### Bước 1: Sửa `.env`

```env
GOOGLE_DRIVE_ENABLED=true
GOOGLE_SERVICE_ACCOUNT_JSON=secrets/service-account-key.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=your_folder_id_here
```

**Thay `your_folder_id_here` bằng Folder ID thực tế:**
- Mở Google Drive: https://drive.google.com/
- Mở folder bạn muốn lưu file
- Copy ID từ URL: `https://drive.google.com/drive/folders/1ABC...XYZ`

### Bước 2: File JSON Service Account
- Đặt file JSON vào: `d:\fpt\tool_be\secrets\service-account-key.json`
- Hoặc đặt đường dẫn khác trong `GOOGLE_SERVICE_ACCOUNT_JSON`

### Bước 3: Chia sẻ folder
1. Lấy email từ file JSON (dòng `"client_email"`)
2. Mở folder trên Google Drive
3. Click **Share** → Paste email → Quyền **Editor**

---

## 🎯 Luồng hoạt động

### Trước (Local Storage):
```
Upload ZIP
   ↓
Giải nén → Lưu ở C:\Users\...\be_tool_reports\
   ↓
Celery xử lý file từ local
   ↓
Lưu vào database
```

### Sau (Google Drive + Local):
```
Upload ZIP
   ↓
Giải nén → Upload lên Google Drive (nếu enabled)
   ↓
Celery download từ Google Drive
   ↓
Xử lý file
   ↓
Lưu vào database (path_storage = gdrive://file_id)
```

---

## 📊 Database

File được lưu trong bảng `report_files` với `path_storage`:

| Loại | path_storage | Ví dụ |
|------|-------------|-------|
| Google Drive | gdrive://ID | `gdrive://1ABC2DEF3GHI4JKL5MNO` |
| Local | /absolute/path | `/home/user/be_tool_reports/report_EXAM001.../file.pdf` |

---

## 🧪 Test

### 1. Check cấu hình
```python
from app.core.google_drive import get_google_drive_manager

gd = get_google_drive_manager()
print(f"Connected: {gd.is_configured}")
```

### 2. Upload file test
```python
folder_id = gd.create_folder("Test")
file_id = gd.upload_file_bytes(b"test", "test.txt", folder_id)
```

---

## ⚠️ Lưu ý

1. **Kiểm tra `.env`** - Chắc chắn `GOOGLE_DRIVE_ENABLED=true`
2. **Folder ID** - Phải là ID thực tế từ Google Drive, không phải URL
3. **Quyền** - Service account phải có quyền **Editor** trên folder
4. **Bảo mật** - Không commit file JSON vào Git (thêm vào `.gitignore`)

---

## 🆘 Troubleshooting

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-----------|----------|
| "Google Drive not configured" | Chưa set biến môi trường | Kiểm tra `.env` |
| "Access denied" | Service account không có quyền | Chia sẻ folder với service account |
| "File not found" | Folder ID sai | Copy lại từ URL |
| Upload chậm | Giới hạn tốc độ Google | Chờ hoặc thử lại |

---

## ✅ Checklist

- [ ] Đặt file JSON service account trong `secrets/`
- [ ] Cập nhật `GOOGLE_DRIVE_ROOT_FOLDER_ID` trong `.env`
- [ ] Enable: `GOOGLE_DRIVE_ENABLED=true`
- [ ] Chia sẻ folder trên Google Drive
- [ ] Restart server: `uvicorn app.main:app --reload`
- [ ] Test upload file ZIP
- [ ] Kiểm tra file trên Google Drive

**Hoàn thành! 🎉 File upload sẽ được lưu trực tiếp lên Google Drive**
