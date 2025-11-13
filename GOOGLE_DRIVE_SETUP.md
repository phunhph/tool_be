# 📁 Hướng dẫn lưu file upload lên Google Drive

## 📋 Yêu cầu

1. Có tài khoản Google Cloud
2. Đã tạo project trên Google Cloud Console
3. Đã enable Google Drive API

## 🔧 Bước 1: Tạo Service Account

### Cách 1: Qua Google Cloud Console

1. Truy cập: https://console.cloud.google.com/
2. Chọn project của bạn
3. Vào **"IAM & Admin"** → **"Service Accounts"**
4. Click **"Create Service Account"**
5. Nhập tên: `file-uploader`
6. Click **"Create and Continue"**
7. Cấp quyền: **"Editor"** hoặc **"Drive Admin"**
8. Click **"Continue"** → **"Done"**

### Bước 2: Tạo Key JSON

1. Click vào service account vừa tạo
2. Vào tab **"Keys"**
3. Click **"Add Key"** → **"Create new key"**
4. Chọn **JSON**
5. Click **"Create"** - file sẽ tự động download

**File này chứa thông tin nhạy cảm - GIỮ KÍN!**

## 📁 Bước 3: Cấp quyền cho Service Account

1. Truy cập Google Drive: https://drive.google.com/
2. Tạo folder để lưu file upload (ví dụ: `Reports`)
3. Copy email của service account từ file JSON (ví dụ: `file-uploader@project-id.iam.gserviceaccount.com`)
4. Chia sẻ folder với service account này với quyền **"Editor"**

## 🔐 Bước 4: Cấu hình ứng dụng

### Cách 1: Dùng file `.env`

Thêm vào file `.env`:

```env
# Google Drive Configuration
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account-key.json
GOOGLE_DRIVE_ENABLED=true
GOOGLE_DRIVE_ROOT_FOLDER_ID=your_folder_id_here
```

### Cách 2: Dùng biến môi trường

```bash
# Windows PowerShell
$env:GOOGLE_SERVICE_ACCOUNT_JSON="C:\path\to\service-account-key.json"
$env:GOOGLE_DRIVE_ENABLED="true"
$env:GOOGLE_DRIVE_ROOT_FOLDER_ID="your_folder_id_here"

# Linux/Mac
export GOOGLE_SERVICE_ACCOUNT_JSON="/path/to/service-account-key.json"
export GOOGLE_DRIVE_ENABLED="true"
export GOOGLE_DRIVE_ROOT_FOLDER_ID="your_folder_id_here"
```

### Cách 3: Copy file JSON vào project

1. Copy file JSON service account vào project, ví dụ:
   ```
   d:\fpt\tool_be\secrets\service-account-key.json
   ```

2. Cấu hình trong `.env`:
   ```env
   GOOGLE_SERVICE_ACCOUNT_JSON=secrets/service-account-key.json
   ```

## 🎯 Cách lấy Folder ID

1. Mở folder trên Google Drive
2. Lấy ID từ URL:
   ```
   https://drive.google.com/drive/folders/1ABC...XYZ
                                            ^^^...^^^
   ```
   ID là phần sau `/folders/`

## 💾 Cách sửa code để dùng Google Drive

### Tùy chọn 1: Dùng Google Drive thay thế Local Storage

Sửa file `app/services/report_service.py`:

```python
from app.core.google_drive import get_google_drive_manager

@staticmethod
def process_zip_upload(db: Session, exam_id: int, zip_bytes: bytes, zip_filename: str, username: str):
    """
    Xử lý upload file ZIP chứa các file PDF báo cáo.
    Lưu vào Google Drive thay vì local storage
    """
    try:
        # ... code kiểm tra exam ...
        
        # Khởi tạo Google Drive
        gd_manager = get_google_drive_manager()
        
        if gd_manager.is_configured:
            # Tạo folder trên Google Drive
            exam = db.query(Exam).filter(Exam.id == exam_id).first()
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            folder_name = f"report_{exam.code}_{timestamp}"
            
            folder_id = gd_manager.create_folder(
                folder_name,
                parent_id=os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")
            )
            
            if not folder_id:
                raise_error(500, "Không thể tạo folder trên Google Drive")
            
            # Upload từng file PDF
            file_metadata = []
            with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zip_ref:
                member_names = [name for name in zip_ref.namelist() 
                               if name.lower().endswith(".pdf")]
                
                for name in member_names:
                    content = zip_ref.read(name)
                    base_name = os.path.basename(name)
                    
                    # Upload bytes lên Google Drive
                    file_id = gd_manager.upload_file_bytes(
                        content,
                        base_name,
                        parent_id=folder_id
                    )
                    
                    if file_id:
                        file_metadata.append({
                            "filename": base_name,
                            "google_drive_id": file_id,
                            "size": len(content)
                        })
            
            # ... tiếp tục xử lý như bình thường ...
        else:
            # Fallback: lưu local nếu Google Drive không cấu hình
            logger.warning("Google Drive not configured, falling back to local storage")
            # ... code lưu local hiện tại ...
            
    except Exception as e:
        logger.error(f"Error: {e}")
        raise_error(500, f"Error: {e}")
```

### Tùy chọn 2: Dùng cả Local Storage và Google Drive

```python
# Lưu vào local
file_path = folder_path / base_name
with open(file_path, "wb") as f:
    f.write(content)

# Đồng thời upload lên Google Drive (nếu cấu hình)
gd_manager = get_google_drive_manager()
if gd_manager.is_configured:
    file_id = gd_manager.upload_file(
        str(file_path),
        parent_id=os.getenv("GOOGLE_DRIVE_ROOT_FOLDER_ID")
    )
```

## 🧪 Test

```python
from app.core.google_drive import get_google_drive_manager

# Lấy manager
gd = get_google_drive_manager()

# Kiểm tra cấu hình
print(f"Google Drive configured: {gd.is_configured}")

# Tạo folder test
folder_id = gd.create_folder("Test Folder")
print(f"Folder ID: {folder_id}")

# Upload file test
file_id = gd.upload_file_bytes(
    b"Test content",
    "test.txt",
    parent_id=folder_id
)
print(f"File ID: {file_id}")
```

## ⚠️ Lưu ý bảo mật

1. **Không commit** file JSON service account vào Git
2. Thêm vào `.gitignore`:
   ```
   secrets/
   *.json
   !package.json
   ```
3. Sử dụng biến môi trường thay vì hardcode
4. Xoay key định kỳ
5. Giới hạn quyền service account

## 🆘 Troubleshooting

### Lỗi: "Invalid service account JSON"

- Kiểm tra đường dẫn file JSON
- Chắc chắn file JSON không bị lỗi

### Lỗi: "Access denied"

- Kiểm tra service account có quyền "Editor" không
- Kiểm tra folder đã được chia sẻ với service account

### Lỗi: "Drive API not enabled"

- Vào Google Cloud Console
- Vào **APIs & Services** → **Library**
- Tìm "Google Drive API"
- Click **Enable**

### Upload chậm

- Google Drive upload có giới hạn tốc độ
- Xem xét dùng `resumable=True` (đã cấu hình mặc định)
- Có thể compress file trước khi upload

## 📚 Tài liệu tham khảo

- Google Drive API: https://developers.google.com/drive/api/guides/about-sdk
- Service Accounts: https://cloud.google.com/iam/docs/service-accounts
- Python Client Library: https://github.com/googleapis/google-api-python-client
