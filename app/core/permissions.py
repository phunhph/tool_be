from fastapi import Depends, HTTPException, status
from app.routers.auth import get_current_user

def require_role(role: str):
    def role_checker(current_user = Depends(get_current_user)):
        if current_user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập chức năng này"
            )
        return current_user
    return role_checker
