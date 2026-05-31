from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import List

# 导入本地模块
from app.schemas import user_schema
from app.core import security
from app.models import base,database

from app.crud import crud

router = APIRouter(prefix="/api/v1/auth", tags=["认证授权"])

# ==========================================
# 注册接口
# ==========================================

@router.post("/register", response_model=user_schema.UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user_in: user_schema.UserCreate, 
    db: Session = Depends(database.get_db)
):
    """
    用户注册
    1. 检查用户名唯一性
    2. 验证租户是否存在
    3. 创建用户并关联租户
    """
    # 1. 检查用户名是否已存在
    if crud.get_user_by_username(db, username=user_in.username):
        raise HTTPException(status_code=400, detail="用户名已被注册")

    # 3. 创建用户
    # crud.create_user 内部会处理密码哈希
    return crud.create_user(db, user_in=user_in)

# ==========================================
# 登录接口
# ==========================================

@router.post("/login", response_model=user_schema.LoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    """
    OAuth2 兼容登录接口
    返回: access_token, token_type, 以及用户完整信息
    """
    # 1. 查找用户 (支持用户名或邮箱登录)
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user:
        # 为了安全，不提示具体是用户名错还是密码错
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 验证密码
    if not security.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )


    # 4. 生成 Access Token
    access_token = security.create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=30) # 设置过期时间为 30 分钟
    )

    # 5. 返回结果
    # 将 SQLAlchemy 模型转换为 Pydantic 模型，并附加 token 信息
    return user_schema.LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user.model_dump() # 包含 id, username等
    )