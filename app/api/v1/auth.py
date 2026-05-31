# 文件路径：app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
from datetime import timedelta

# 导入本地模块
from app import schemas, crud
from app.core import security
from app.models import base, database
from . import deps  # 导入刚才创建的依赖模块

router = APIRouter()

# ==========================================
# 注册与租户接口
# ==========================================

@router.get("/tenants", response_model=List[schemas.TenantOut])
def read_tenants(db: Session = Depends(database.get_db)):
    """获取所有租户，供注册页面选择"""
    tenants = db.query(base.TenantDB).all()
    return tenants

@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user_in: schemas.UserCreate, 
    db: Session = Depends(database.get_db)
):
    """用户注册接口"""
    # 1. 检查用户名是否已存在
    if crud.get_user_by_username(db, username=user_in.username):
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 2. 校验租户ID
    if not user_in.tenant_id:
         raise HTTPException(status_code=400, detail="必须选择所属租户")

    # 3. 创建用户
    return crud.create_user(db, user_in=user_in, tenant_id=user_in.tenant_id)

# ==========================================
# 登录接口
# ==========================================

@router.post("/login", response_model=schemas.LoginResponse)
async def login(
    form_data: deps.OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):
    """
    OAuth2 兼容登录接口
    """
    # 1. 验证用户
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 2. 生成 Token
    access_token = security.create_access_token(
        subject=str(user.id), # 确保转为字符串
        expires_delta=timedelta(minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # 3. 返回结果
    return schemas.LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user.model_dump()
    )