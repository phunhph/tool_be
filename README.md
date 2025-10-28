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

pp/
├── main.py # Điểm khởi chạy ứng dụng FastAPI
├── core/ # Cấu hình & bảo mật
│ ├── security.py # Xử lý JWT, mã hóa mật khẩu
│ └── config.py # Cấu hình ứng dụng
│
├── models/ # Các model SQLAlchemy
│ ├── user.py # Model User
│ ├── role.py # Model Role
│ └── exam.py # Model Exam
│
├── schemas/ # Các schema (Pydantic)
│ ├── base_schemas.py # Các schema cơ bản (ListResponse, CreateResponse,…)
│ └── exam_schemas.py # Schema cho module Exam
│
├── services/ # Xử lý logic CRUD và nghiệp vụ
│ ├── auth_service.py # Đăng nhập, tạo token
│ ├── user_service.py # CRUD User
│ └── exam_service.py # CRUD Exam
│
├── api/ # Định nghĩa các endpoint
│ ├── auth_api.py # Endpoint: /auth/login
│ ├── exam_api.py # Endpoint: /exams
│ └── user_api.py # Endpoint: /users
│
├── database/ # Cấu hình cơ sở dữ liệu
│ ├── base.py # Base class cho SQLAlchemy
│ └── session.py # Khởi tạo session DB
│
└── tests/ # Unit test bằng pytest                    # Unit test bằng pytest

---

## 🔐 Phân quyền hệ thống

| Role         | Mô tả                              | Quyền hạn chính |
|---------------|------------------------------------|------------------|
| **master**    | Tài khoản quản trị cao nhất        | Full quyền (CRUD users, roles, exams) |
| **Admin**     | Có thể xem, tạo, sửa, xóa trừ thay đổi quyền và xoá user             | Chỉ được `POST`, `PUT` và `GET` |
| **view+export** | Người xem & xuất dữ liệu          | Chỉ được `GET` |

> ⚠️ Chỉ `role: master` mới được chỉnh sửa quyền người dùng khác.

---

## 🚀 Cách cài đặt và chạy dự án

### 1️⃣ Clone project
```bash
git https://github.com/phunhph/tool_be
cd tool_be
```

### 2️⃣ Cài đặt thư viện
```bash
pip install -r requirements.txt || python -m pip install -r requirements.txt 
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
alembic upgrade head ||  python -m alembic upgrade head 
```

### 5️⃣ Chạy sending
```bash
 python -m scripts.seed_roles
```

### 5️⃣ Chạy server
```bash
uvicorn app.main:app --reload ||  python -m uvicorn app.main:app  --reload 
```
# 🚨 DÙNG EVENTLET (hoặc gevent)
celery -A app.core.celery_app worker -P eventlet --loglevel=info -c 5 || python -m celery -A app.core.celery_app worker -P eventlet --loglevel=info -c 5
python -m celery -A app.core.celery_app worker -P solo --loglevel=info
API chạy tại: 👉 [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📘 API Reference

### 🔑 **Đăng nhập**

**POST** `api/auth/login`

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
**POST** `/api/exams`

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
**GET** `/api/users?page=1&page_size=10`

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
**PUT** `api/exams/1`

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
**DELETE** `api/exams/1`

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

**Nguyễn Hữu Phú(PhuNH)**  
📧 Email: phunh@hblab.vn  
💻 Dự án cá nhân dùng để học và quản lý dữ liệu thi cử.

---

## 🧾 Giấy phép

MIT License © 2025 Nguyễn Hữu Phú(PhuNH)
