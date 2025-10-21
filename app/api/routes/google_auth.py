from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
from app.db import get_db
from app.models.user import User
from app.api.routes.auth import create_access_token
import os

router = APIRouter(
    prefix="/auth",
    tags=["Auth - Google"]
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

@router.post(
    "/google",
    summary="Đăng nhập bằng Google",
)
def login_with_google(token: str, db: Session = Depends(get_db)):
    """
    Xác thực người dùng thông qua Google OAuth và trả về access token JWT.
    """
    try:
        # Xác minh token Google
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)

        email = idinfo.get("email")
        name = idinfo.get("name", "")
        first_name, *last = name.split(" ", 1)
        last_name = last[0] if last else ""

        # Kiểm tra user đã tồn tại chưa
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                first_name=first_name,
                last_name=last_name,
                email=email,
                login_id=email,
                password="",
                role="user",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # Tạo JWT token
        access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
        return {"access_token": access_token, "token_type": "bearer"}

    except ValueError:
        raise HTTPException(status_code=400, detail="Token Google không hợp lệ")
