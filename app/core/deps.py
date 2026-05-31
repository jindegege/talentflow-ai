# app/api/v1/deps.py
from fastapi import Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core import security
from app.models import base,database

from fastapi.security import OAuth2PasswordBearer

# 定义 OAuth2 方案 (可以放在这里，也可以放在 security.py)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.settings.SECRET_KEY, algorithms=[security.settings.ALGORITHM])
        user_id: str = payload.get("sub")
        print(f"user_id === {user_id}")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
        
    user = db.execute(select(base.UserDB).where(base.UserDB.id == int(user_id))).scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_admin(current_user: base.UserDB = Depends(get_current_user)):
    if current_user.role != 1:
        raise HTTPException(status_code=403, detail="权限不足：仅管理员可操作")
    return current_user


def get_current_active_user(current_user: base.UserDB = Depends(get_current_user)):
    if current_user.role != 2:
        raise HTTPException(status_code=403, detail="权限不足：仅导师可操作")
    return current_user