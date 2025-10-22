from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, CreateResponse
from app.schemas.base_schemas import DetailResponse, ListResponse
from app.models import User, Role
from app.api.routes.auth import get_current_user, require_role
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])

# ---------------- GET LIST ----------------
@router.get("/", response_model=ListResponse[UserResponse], summary="Lấy danh sách người dùng")
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["viewer", "admin"]))
):
    # master/admin đều xem được tất cả
    return UserService.get_users(db)

# ---------------- GET DETAIL ----------------
@router.get("/{user_id}", response_model=DetailResponse, summary="Xem chi tiết người dùng")
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user = UserService.get_user(db, user_id)
    # Kiểm tra quyền: user bình thường chỉ xem chính mình
    if current_user.role_id != 1 and current_user.id != user_id:  # role_id 1 = master
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role.name != "admin":
            raise HTTPException(status_code=403, detail="Không có quyền xem người dùng khác")
    return user

# ---------------- CREATE ----------------
@router.post("/", response_model=CreateResponse, summary="Tạo người dùng mới")
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    return UserService.create_user(db, payload)

# ---------------- UPDATE ----------------
@router.put("/{user_id}", response_model=UserResponse, summary="Cập nhật thông tin người dùng")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # user chỉ update chính mình, master/admin update được tất cả
    if current_user.role_id != 1 and current_user.id != user_id:
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role.name != "admin":
            raise HTTPException(status_code=403, detail="Không có quyền cập nhật người dùng khác")
    return UserService.update_user(db, user_id, payload)

# ---------------- DELETE ----------------
@router.delete("/{user_id}", summary="Xóa người dùng")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    # master/admin mới được xóa
    return UserService.delete_user(db, user_id)
