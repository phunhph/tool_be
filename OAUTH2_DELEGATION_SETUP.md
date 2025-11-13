# 🔐 Cấu hình OAuth2 Delegation cho Google Drive

## ❓ Vấn đề
Service Account không thể upload file lên personal Google Drive vì **không có storage quota**.

## ✅ Giải pháp: OAuth2 Delegation
Cho phép Service Account upload **như bạn** (với quyền của bạn).

---

## 🔧 Cấu hình (5 bước)

### Bước 1: Enable Domain-Wide Delegation

1. Vào **Google Cloud Console**: https://console.cloud.google.com/
2. Chọn project của bạn
3. Vào **APIs & Services** → **Service Accounts**
4. Click vào service account (`file-uploader@...`)
5. Tab **Details** → Scroll down
6. Tìm **Google Workspace Domain-wide Delegation**
7. Click **Enable** (nếu chưa bật)
8. Lưu lại **Client ID** (ví dụ: `1234567890`)

### Bước 2: Add OAuth Scopes (Admin Console)

1. Vào **Google Workspace Admin Console**: https://admin.google.com/
2. Vào **Security** → **API Controls** → **Domain-wide delegation**
3. Click **Add new**
4. **Client ID**: Paste Client ID từ Bước 1 (ví dụ: `1234567890`)
5. **OAuth Scopes**: Paste: 
   ```
   https://www.googleapis.com/auth/drive
   ```
6. Click **Authorize**

### Bước 3: Update `.env`

```env
GOOGLE_OAUTH_USER_EMAIL=your-email@yourdomain.com
```

**Thay `your-email@yourdomain.com` bằng email Google Workspace của bạn!**

Ví dụ:
```env
GOOGLE_OAUTH_USER_EMAIL=phu@company.com
```

### Bước 4: Tạo folder trên Google Drive của bạn

1. Mở Google Drive: https://drive.google.com/
2. Tạo folder: `Reports`
3. Copy Folder ID từ URL: 
   ```
   https://drive.google.com/drive/folders/1ABC...XYZ
   ```
4. Set trong `.env`:
   ```env
   GOOGLE_DRIVE_ROOT_FOLDER_ID=1ABC...XYZ
   ```

### Bước 5: Restart Server

```bash
# Restart uvicorn
Ctrl+C
uvicorn app.main:app --reload
```

---

## ✨ Kết quả

Sau khi cấu hình:
- ✅ Folder được tạo trên **Google Drive của bạn**
- ✅ File được upload như **bạn** upload (không phải service account)
- ✅ Không có quota limit
- ✅ Fallback local nếu cần

---

## ⚠️ Lưu ý quan trọng

### Điều kiện cần:
1. ✅ Phải có **Google Workspace account** (không phải Gmail cá nhân)
   - Gmail cá nhân: `user@gmail.com` ❌
   - Google Workspace: `user@company.com` ✅

2. ✅ Phải là **admin** của Google Workspace

### Nếu dùng Gmail cá nhân:
- OAuth2 delegation **không hoạt động**
- Fallback: Dùng **Shared Drive** thay vào

---

## 🆘 Troubleshooting

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-----------|----------|
| "Invalid subject" | Email sai | Kiểm tra `GOOGLE_OAUTH_USER_EMAIL` |
| "Not authorized" | Domain-wide delegation chưa setup | Làm lại Bước 1-2 |
| "Access denied" | Email không admin | Thêm email vào admin console |

---

## 📝 Checklist

- [ ] Enable Domain-Wide Delegation trên Service Account
- [ ] Add OAuth Scopes trên Admin Console
- [ ] Copy Client ID và OAuth Scopes
- [ ] Set `GOOGLE_OAUTH_USER_EMAIL` trong `.env`
- [ ] Tạo folder trên Google Drive
- [ ] Set `GOOGLE_DRIVE_ROOT_FOLDER_ID` trong `.env`
- [ ] Restart server
- [ ] Test upload file

**Hoàn thành! 🎉**
