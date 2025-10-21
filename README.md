# 🧠 Exam Management API

Hệ thống quản lý kỳ thi (Exam Management) được xây dựng bằng **FastAPI** với tính năng xác thực JWT, phân quyền theo Role, và các API CRUD cho module `Exam`.

---

## ⚙️ Công nghệ sử dụng

- **FastAPI** — Framework chính cho backend  
- **SQLAlchemy** — ORM thao tác cơ sở dữ liệu  
- **Pydantic** — Xác thực dữ liệu đầu vào/đầu ra  
- **JWT** — Xác thực và phân quyền người dùng  
- **SQLite / PostgreSQL** — Hệ quản trị cơ sở dữ liệu  
- **Alembic** — Quản lý migration  

---

## 📁 Cấu trúc thư mục

app/
 ├── main.py                     # Điểm khởi chạy ứng dụng FastAPI
 ├── core/
 │   ├── security.py             # Xử lý JWT, mã hóa mật khẩu
 │   └── config.py               # Cấu hình ứng dụng
 ├── models/
 │   ├── user.py                 # Model User
 │   ├── role.py                 # Model Role
 │   └── exam.py                 # Model Exam
 ├── schemas/
 │   ├── base_schemas.py         # Các schema cơ bản (ListResponse, CreateResponse,…)
 │   └── exam_schemas.py         # Schema cho module Exam
 ├── services/
 │   ├── auth_service.py         # Đăng nhập, tạo token
 │   ├── user_service.py         # CRUD User
 │   └── exam_service.py         # CRUD Exam
 ├── api/
 │   ├── auth_api.py             # Endpoint: /auth/login
 │   ├── exam_api.py             # Endpoint: /exams
 │   └── user_api.py             # Endpoint: /users
 ├── database/
 │   ├── base.py                 # Base class cho SQLAlchemy
 │   └── session.py              # Khởi tạo session DB
 └── tests/                      # Unit test bằng pytest

---

## 🔐 Phân quyền hệ thống

| Role         | Mô tả                              | Quyền hạn chính |
|---------------|------------------------------------|------------------|
| **master**    | Tài khoản quản trị cao nhất        | Full quyền (CRUD users, roles, exams) |
| **create**    | Người tạo dữ liệu                  | Chỉ được `POST` và `GET` |
| **update**    | Người chỉnh sửa dữ liệu            | Chỉ được `PUT` và `GET` |
| **view+export** | Người xem & xuất dữ liệu          | Chỉ được `GET` |
| **normal**    | Người dùng thông thường            | Hạn chế quyền |

> ⚠️ Chỉ `role: master` mới được chỉnh sửa quyền người dùng khác.

---

## 🚀 Cách cài đặt và chạy dự án

### 1️⃣ Clone project
```bash
git clone https://github.com/yourname/exam-api.git
cd exam-api
```

### 2️⃣ Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### 3️⃣ Tạo file môi trường `.env`
```bash
DATABASE_URL=sqlite:///./test.db
SECRET_KEY=supersecret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 4️⃣ Chạy migration
```bash
alembic upgrade head
```

### 5️⃣ Chạy server
```bash
uvicorn app.main:app --reload
```

API chạy tại: 👉 [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📘 API Reference

### 🔑 **Đăng nhập**

**POST** `/auth/login`

**Body**
```json
{
  "username": "admin",
  "password": "123456"
}
```

**Response**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

### 📚 **Exam API**

#### ➕ Tạo mới kỳ thi
**POST** `/exams`

```json
{
  "name": "Kỳ thi học kỳ 1",
  "code": "EXAM001",
  "start_time": "2025-10-22T08:00:00",
  "end_time": "2025-10-22T10:00:00"
}
```

**Response**
```json
{
  "message": "Exam created successfully",
  "status": true,
  "examId": 1
}
```

---

#### 📋 Danh sách kỳ thi
**GET** `/exams?page=1&page_size=10`

**Response**
```json
{
  "data": [
    {
      "id": 1,
      "name": "Kỳ thi học kỳ 1",
      "code": "EXAM001",
      "start_time": "2025-10-22T08:00:00",
      "end_time": "2025-10-22T10:00:00"
    }
  ],
  "total": 1,
  "page_size": 10,
  "page_index": 1
}
```

---

#### ✏️ Cập nhật kỳ thi
**PUT** `/exams/1`

```json
{
  "name": "Kỳ thi HK1 - Cập nhật"
}
```

**Response**
```json
{
  "message": "Exam updated successfully",
  "status": true,
  "data": {
    "id": 1,
    "name": "Kỳ thi HK1 - Cập nhật",
    "code": "EXAM001",
    "start_time": "2025-10-22T08:00:00",
    "end_time": "2025-10-22T10:00:00"
  }
}
```

---

#### ❌ Xóa kỳ thi
**DELETE** `/exams/1`

**Response**
```json
{
  "message": "Exam deleted successfully",
  "status": true,
  "examId": 1
}
```

---

## 🧪 Test bằng Postman

### 🧩 Tự động lưu token
Trong tab **Tests** của request **Login**, thêm đoạn script:

```javascript
if (pm.response.code === 200) {
    var jsonData = pm.response.json();
    pm.environment.set("token", jsonData.access_token);
    console.log("✅ Token đã được lưu:", jsonData.access_token);
} else {
    console.log("❌ Login thất bại!");
}
```

### 🔐 Gán token cho các request khác
Trong tab **Authorization** của các API khác:
```
Type: Bearer Token
Token: {{token}}
```

---

## 🧍‍♂️ Tác giả

**Phú B2**  
📧 Email: youremail@example.com  
💻 Dự án cá nhân dùng để học và quản lý dữ liệu thi cử.

---

## 🧾 Giấy phép

MIT License © 2025 Phú B2
