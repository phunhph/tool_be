from psycopg2 import IntegrityError
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserResponse, CreateResponse, DeleteResponse
from app.schemas.base_schemas import DetailResponse
from app.schemas.user import UserCreate
from fastapi import HTTPException
from passlib.context import CryptContext

class UserService:
    @staticmethod
    def get_users(db: Session):
        users = db.query(User).filter(User.is_delete==False).all()
        return [
            UserResponse(
                id=u.id,
                login_id=u.login_id,
                first_name=u.first_name,
                last_name=u.last_name,
                email=u.email,
                role=u.role.name if u.role else "",  # <--- map từ Role object
                is_delete=u.is_delete
            )
            for u in users
        ]

    @staticmethod
    def get_user(db: Session, user_id: int):
        user = db.query(User).filter(User.id == user_id, User.is_delete == False).first()
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        return DetailResponse(
            status=True,
            data=UserResponse(
                id=user.id,
                login_id=user.login_id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                role=user.role.name if user.role else "",  # <--- map từ Role object
                is_delete=user.is_delete
            )
        );
        
    def create_user(db: Session, payload: UserCreate):
        pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        # Check login_id
        exists_login = db.query(User).filter(User.login_id == payload.login_id).first()
        if exists_login:
            raise HTTPException(status_code=400, detail="login_id đã tồn tại")
        
        # Check email
        exists_email = db.query(User).filter(User.email == payload.email).first()
        if exists_email:
            raise HTTPException(status_code=400, detail="Email đã tồn tại")

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
            raise HTTPException(status_code=400, detail="Tạo user thất bại do trùng thông tin")

        return CreateResponse(
            message="Tạo người dùng thành công",
            status=True,
            userId=new_user.id
        )

    @staticmethod
    def delete_user(db: Session, user_id: int):
        user = db.query(User).filter(User.id == user_id, User.is_delete != True).first()
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
        user.is_delete = True
        db.commit()
        return DeleteResponse(
                message="Xóa người dùng thành công",
                status=True,
                userId=user.id
            );
