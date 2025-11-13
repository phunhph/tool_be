# 🚀 Tích hợp Google Drive - Hướng dẫn nhanh

## 📌 Tóm tắt

Bạn có thể lưu file upload lên Google Drive thay vì local storage. Đã cài đặt 3 file mới:

### 1. **`app/core/google_drive.py`** 
   - Module chính để xử lý upload/download Google Drive
   - Quản lý authentication, tạo folder, upload file

### 2. **`app/services/google_drive_mixin.py`**
   - Mixin class để thêm vào ReportService
   - Chứa các helper method

### 3. **`GOOGLE_DRIVE_SETUP.md`**
   - Hướng dẫn chi tiết cấu hình Google Drive
   - Cách tạo Service Account, lấy key JSON

### 4. **`GOOGLE_DRIVE_USAGE_EXAMPLES.py`**
   - Ví dụ cách sử dụng

### 5. **`app/core/config.py`** - Cập nhật
   - Thêm biến cấu hình: `GOOGLE_DRIVE_ENABLED`, `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_DRIVE_ROOT_FOLDER_ID`

### 6. **`.env.example`** - Cập nhật
   - Thêm mẫu cấu hình Google Drive

---

## ⚡ Quick Start (5 phút)

### Bước 1: Cài đặt thư viện
```bash
pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Bước 2: Tạo Service Account
1. Truy cập: https://console.cloud.google.com/
2. Vào **IAM & Admin** → **Service Accounts**
3. Click **Create Service Account**
4. Đặt tên: `file-uploader`
5. Cấp quyền: **Editor**
6. Tạo Key → JSON → Download

### Bước 3: Copy key vào project
```bash
# Tạo thư mục secrets
mkdir secrets

# Copy file JSON vào thư mục
cp ~/Downloads/service-account-key.json secrets/
```

### Bước 4: Cấu hình `.env`
```env
GOOGLE_DRIVE_ENABLED=true
GOOGLE_SERVICE_ACCOUNT_JSON=secrets/service-account-key.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=your_folder_id_here
```

### Bước 5: Chia sẻ folder trên Google Drive
1. Mở Google Drive: https://drive.google.com/
2. Tạo folder (ví dụ: `Reports`)
3. Copy ID từ URL: `https://drive.google.com/drive/folders/1ABC...XYZ`
4. Chia sẻ với email service account (có trong file JSON)

### Bước 6: Test
```python
from app.core.google_drive import get_google_drive_manager

gd = get_google_drive_manager()
print(f"Connected: {gd.is_configured}")
```

---

## 🎯 Cách sử dụng trong code

### Option 1: Chỉ dùng Google Drive
```python
from app.services.google_drive_mixin import GoogleDriveUploadMixin

# Tạo folder
folder_id = GoogleDriveUploadMixin._create_google_drive_folder("My Reports")

# Upload file bytes
file_id = GoogleDriveUploadMixin._upload_bytes_to_google_drive(
    file_bytes,
    "report.pdf",
    parent_folder_id=folder_id
)
```

### Option 2: Lưu local + Google Drive
```python
# Lưu local như bình thường
with open(file_path, "wb") as f:
    f.write(content)

# Đồng thời upload lên Google Drive
if settings.GOOGLE_DRIVE_ENABLED:
    GoogleDriveUploadMixin._upload_to_google_drive(
        file_path,
        file_name,
        parent_folder_id=folder_id
    )
```

---

## 📂 File được lưu ở đâu?

### Hiện tại (Local):
```
C:\Users\PhuNH\be_tool_reports\
├── report_EXAM001_20251113_082133\
│   ├── file1.pdf
│   ├── file2.pdf
│   └── ...
```

### Với Google Drive:
```
Google Drive/
├── Reports (root folder)
│   ├── report_EXAM001_20251113_082133/
│   │   ├── file1.pdf
│   │   ├── file2.pdf
│   │   └── ...
```

---

## ⚙️ Cấu hình nâng cao

### Backup vào cả Local và Google Drive
Sửa `report_service.py` để enable cả hai:

```python
# Lưu local
file_path = folder_path / base_name
with open(file_path, "wb") as f:
    f.write(content)

# Backup lên Google Drive nếu enabled
if settings.GOOGLE_DRIVE_ENABLED:
    gdrive_id = GoogleDriveUploadMixin._upload_to_google_drive(
        str(file_path),
        base_name,
        parent_folder_id=gdrive_folder_id
    )
    # Lưu Google Drive ID vào database
    new_report_file.google_drive_id = gdrive_id
```

### Chỉ dùng Google Drive (không local)
Xoá code lưu local, chỉ upload lên Google Drive

---

## 🔒 Bảo mật

⚠️ **QUAN TRỌNG**: Không commit file JSON vào Git!

```gitignore
# .gitignore
secrets/
*.json
!package.json
```

---

## 🆘 Troubleshooting

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-----------|----------|
| "Google Drive not configured" | Chưa set biến môi trường | Kiểm tra `.env` |
| "Access denied" | Service account không có quyền | Chia sẻ folder với service account |
| "Drive API not enabled" | API chưa bật | Bật ở Google Cloud Console |
| "File not found" | Đường dẫn sai | Kiểm tra đường dẫn file JSON |

---

## 📚 Tài liệu

- Hướng dẫn chi tiết: `GOOGLE_DRIVE_SETUP.md`
- Ví dụ sử dụng: `GOOGLE_DRIVE_USAGE_EXAMPLES.py`
- API docs: https://developers.google.com/drive/api

---

## ✅ Checklist cấu hình

- [ ] Cài đặt thư viện Google Drive
- [ ] Tạo Service Account trên Google Cloud
- [ ] Download file JSON key
- [ ] Copy key vào `secrets/` folder
- [ ] Set `GOOGLE_DRIVE_ENABLED=true` trong `.env`
- [ ] Set `GOOGLE_SERVICE_ACCOUNT_JSON` path
- [ ] Tạo folder trên Google Drive
- [ ] Set `GOOGLE_DRIVE_ROOT_FOLDER_ID` 
- [ ] Chia sẻ folder với service account
- [ ] Test kết nối
- [ ] Update `report_service.py` để dùng Google Drive

**Hoàn thành! 🎉**
