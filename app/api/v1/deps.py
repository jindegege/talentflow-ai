# app/api/v1/deps.py
from fastapi import Depends, HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core import security
from app.models import base, database

from app.core import security

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

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
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
        
    user = db.execute(select(base.UserDB).where(base.UserDB.id == int(user_id))).scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

# ==========================================
# 2. 新增：获取当前租户 ID 的依赖
# 目标：这是实现数据隔离的核心。
# 业务层（Service/CRUD）将依赖此函数来自动获得当前租户的过滤条件。
# ==========================================
def get_current_tenant_id(
    current_user: base.UserDB = Depends(get_current_user)
) -> int:
    """
    从当前登录用户中提取 tenant_id。
    如果用户没有租户（理论上不应该发生），抛出 403 错误。
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="用户未关联租户，无法访问数据"
        )
    return current_user.tenant_id

def get_current_active_admin(current_user: base.UserDB = Depends(get_current_user)):
    if current_user.role != 1:
        raise HTTPException(status_code=403, detail="权限不足：仅管理员可操作")
    return current_user