from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserResponse, CreateResponse, DeleteResponse
from app.schemas.base_schemas import DetailResponse, ListResponse
from app.schemas.user import UserCreate
from fastapi import HTTPException
from passlib.context import CryptContext

# Helper cho lỗi
def raise_error(status: int, message: str):
    raise HTTPException(status_code=status, detail={"status": status, "message": message})

class UserService:
    @staticmethod
    def get_users(db: Session, page: int = 1, page_size: int = 20):
        users = db.query(User).filter(User.is_delete==False)
        total = users.count()
        users = users.offset((page - 1) * page_size).limit(page_size).all()
        return ListResponse(
            data=[
                UserResponse(
                    id=u.id,
                    login_id=u.login_id,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    email=u.email,
                    role=u.role.name if u.role else "",
                    is_delete=u.is_delete
                )
                for u in users
            ],
            total=total,
            pageSize=page_size,
            pageIndex=page
        )
    
    @staticmethod
    def get_user(db: Session, user_id: int):
        user = db.query(User).filter(User.id == user_id, User.is_delete == False).first()
        if not user:
            raise_error(404, "Không tìm thấy người dùng")
        return DetailResponse(
            status=True,
            data=UserResponse(
                id=user.id,
                login_id=user.login_id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                role=user.role.name if user.role else "",
                is_delete=user.is_delete
            )
        )
    
    @staticmethod
    def create_user(db: Session, payload: UserCreate):
        pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

        # Check login_id
        exists_login = db.query(User).filter(User.login_id == payload.login_id).first()
        if exists_login:
            raise_error(400, "login_id đã tồn tại")
        
        # Check email
        exists_email = db.query(User).filter(User.email == payload.email).first()
        if exists_email:
            raise_error(400, "Email đã tồn tại")

        # Hash password
        hashed_password = pwd_context.hash(payload.password)
        
        new_user = User(
            **payload.dict(exclude={"password"}),
            password=hashed_password
        )
        
        db.add(new_user)
        try:
            db.commit()
            db.refresh(new_user)
        except IntegrityError:
            db.rollback()
            raise_error(400, "Tạo user thất bại do trùng thông tin")

        return CreateResponse(
            message="Tạo người dùng thành công",
            status=True,
            userId=new_user.id
        )

    @staticmethod
    def delete_user(db: Session, user_id: int):
        user = db.query(User).filter(User.id == user_id, User.is_delete != True).first()
        if not user:
            raise_error(404, "Không tìm thấy người dùng")
        user.is_delete = True
        db.commit()
        return DeleteResponse(
            message="Xóa người dùng thành công",
            status=True,
            userId=user.id
        )
