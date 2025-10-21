from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db import get_db
from app.models.user import User
from app.schemas.auth import Token, UserResponse
import os

router = APIRouter(
    prefix="/auth",
    tags=["Auth - Login"],
)

# -------- CONFIG ----------
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
SECRET_KEY = os.getenv("JWT_SECRET_KEY")

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Bộ nhớ tạm cho refresh token (demo)
REFRESH_TOKENS = {}  # {user_id: refresh_token}


# -------- UTILS ----------
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(user_id: int, role_name: str, expires_delta: timedelta | None = None):
    to_encode = {"sub": str(user_id), "role": role_name}
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: int):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# -------- LOGIN ----------
@router.post("/login", response_model=Token, summary="Đăng nhập bằng form (username & password)")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login_id == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")
    if user.is_delete:
        raise HTTPException(status_code=400, detail="Tài khoản đã bị khóa")

    role_name = user.role.name if user.role else None
    access_token = create_access_token(user.id, role_name)
    refresh_token = create_refresh_token(user.id)

    REFRESH_TOKENS[user.id] = refresh_token

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


# -------- CURRENT USER ----------
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role_name: str = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")
    # đồng bộ role name từ token
    user.role_name = role_name
    return user


# -------- ROLE CHECKER ----------
def require_role(required_roles: list[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role.name == "master":
            return current_user  
        if current_user.role.name not in required_roles:
            raise HTTPException(status_code=403, detail="Không có quyền truy cập")
        return current_user
    return role_checker


# -------- ME ----------
@router.get("/me", response_model=UserResponse, summary="Lấy thông tin người dùng hiện tại")
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


# -------- REFRESH TOKEN ----------
@router.post("/refresh", summary="Làm mới access token")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Không phải refresh token")

        user_id = int(payload.get("sub"))
        if REFRESH_TOKENS.get(user_id) != refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token không hợp lệ")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Không tìm thấy người dùng")

        role_name = user.role.name if user.role else None
        new_access_token = create_access_token(user.id, role_name)
        return {"access_token": new_access_token, "token_type": "bearer"}

    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ hoặc đã hết hạn")


# -------- LOGOUT ----------
@router.post("/logout", summary="Đăng xuất (xóa refresh token)")
def logout(current_user: User = Depends(get_current_user)):
    if current_user.id in REFRESH_TOKENS:
        REFRESH_TOKENS.pop(current_user.id)
    return {"message": "Đăng xuất thành công"}
