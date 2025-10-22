from pydantic import BaseModel, EmailStr
from typing import Optional

# Schema cơ bản
class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    is_delete: bool = False

# Dùng để tạo user
class UserCreate(UserBase):
    login_id: str
    password: str
    role_id: int  # lưu role_id khi tạo user

# Dùng để update user
class UserUpdate(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[EmailStr]
    password: Optional[str]
    role_id: Optional[int]

# Schema trả về
class UserResponse(BaseModel):
    id: int
    login_id: str
    first_name: str
    last_name: str
    email: EmailStr
    role: str  # sẽ map từ user.role.name
    is_delete: bool

    class Config:
        from_attributes = True

class CreateResponse(BaseModel):
    message: str
    status: bool
    userId: int

class DeleteResponse(BaseModel):
    message: str
    status: bool
    userId: int

class UpdateResponse(BaseModel):
    message: str
    status: bool
    data: UserResponse