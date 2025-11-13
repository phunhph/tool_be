# 🔧 Giải pháp cho lỗi Google Drive Storage Quota

## ❌ Lỗi gặp phải

```
Error 403: Service Accounts do not have storage quota. 
Leverage shared drives or use OAuth delegation instead.
```

## 🎯 Nguyên nhân

Service Account không có storage quota riêng. Nó chỉ có thể:
1. Upload vào **Shared Drives** (Ổ đĩa công dụng)
2. Upload vào folder được chia sẻ với **OAuth2 delegation**

## ✅ Giải pháp (2 cách)

### **Cách 1: Dùng Shared Drive (Khuyên dùng)**

#### Bước 1: Tạo Shared Drive
1. Truy cập Google Drive Admin: https://admin.google.com/
2. Vào **Drive and Docs** → **Shared drives**
3. Click **New** → Tạo shared drive
4. Đặt tên: `Reports` (hoặc tên khác)

#### Bước 2: Chia sẻ với Service Account
1. Mở shared drive vừa tạo
2. Click **Members**
3. Thêm email service account: `file-uploader@project-id.iam.gserviceaccount.com`
4. Quyền: **Manager**

#### Bước 3: Lấy Shared Drive ID
- Mở shared drive, copy ID từ URL:
  ```
  https://drive.google.com/drive/u/0/folders/0ABC...XYZ?resourcekey=abc...
  ```
- ID là phần sau `/folders/`

#### Bước 4: Update `.env`
```env
GOOGLE_DRIVE_ENABLED=true
GOOGLE_SERVICE_ACCOUNT_JSON=secrets/service-account-key.json
GOOGLE_DRIVE_ROOT_FOLDER_ID=0ABC...XYZ
```

---

### **Cách 2: Dùng OAuth2 Delegation (Phức tạp hơn)**

#### Bước 1: Enable Domain-Wide Delegation
1. Vào Google Cloud Console
2. **APIs & Services** → **Service Accounts**
3. Click vào service account
4. Tab **Details** → Scroll down → **Enable Google Workspace Domain-wide Delegation**
5. Click **Save**

#### Bước 2: Add OAuth Scopes
1. Vào **Security** → **API Controls** → **Domain-wide delegation**
2. Click **Add new**
3. Paste Client ID của service account
4. Scopes: `https://www.googleapis.com/auth/drive`

#### Bước 3: Cấu hình trong code
```python
from google.oauth2 import service_account

# Load service account
creds = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/drive']
)

# Delegate to user
delegated_creds = creds.with_subject('your-email@yourdomain.com')
```

---

## 🔄 Tạm thời: Fallback về Local Storage

Hiện tại, code đã được cập nhật để **automatically fallback** về local storage khi Google Drive upload thất bại:

```env
GOOGLE_DRIVE_ENABLED=false  # Tạm dùng local storage
```

### Cách hoạt động:
1. Nếu `GOOGLE_DRIVE_ENABLED=true` → Upload lên Google Drive
2. Nếu Google Drive fail → **Tự động lưu local**
3. Nếu `GOOGLE_DRIVE_ENABLED=false` → Upload local ngay

---

## 📋 Bảng so sánh

| Phương pháp | Độ phức tạp | Chi phí | Ưu điểm |
|------------|-----------|--------|--------|
| **Shared Drive** | Trung bình | Free | ✅ Đơn giản, không cần code |
| **OAuth2 Delegation** | Cao | Free | ✅ Linh hoạt, full control |
| **Local Storage** | Thấp | Free | ✅ Nhanh, không phụ thuộc Google |

---

## 🚀 Khuyến nghị

### Ngắn hạn:
- Dùng **Local Storage** (hiện tại đã fallback tự động)

### Dài hạn:
- Nâng cấp lên **Shared Drive** (đơn giản nhất)
- Hoặc implement **OAuth2 Delegation** (nếu cần)

---

## 📝 Checklist để enable Google Drive

- [ ] Tạo Shared Drive hoặc configure OAuth2
- [ ] Thêm Service Account vào Shared Drive (quyền Manager)
- [ ] Lấy Shared Drive ID
- [ ] Set `GOOGLE_DRIVE_ENABLED=true` trong `.env`
- [ ] Set `GOOGLE_DRIVE_ROOT_FOLDER_ID=shared_drive_id`
- [ ] Restart server
- [ ] Test upload

---

## 🆘 Troubleshooting

| Vấn đề | Giải pháp |
|--------|----------|
| Vẫn lỗi 403 | Kiểm tra Service Account có trong Shared Drive không |
| Không tìm thấy Shared Drive | Vào https://admin.google.com/ để xem |
| Upload chậm | Dùng Local Storage, Google Drive chỉ backup |

---

## 📚 Tài liệu

- **Shared Drives**: https://developers.google.com/workspace/drive/api/guides/about-shareddrives
- **OAuth2 Delegation**: https://support.google.com/a/answer/7281227
- **Service Accounts**: https://cloud.google.com/iam/docs/service-accounts
