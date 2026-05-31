from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from typing import List, Optional
from app.models.user import User
from app.models.database import get_db
from app.core.security import get_password_hash # 假设你有这个工具函数
from app.core.deps import get_current_active_admin # 假设你有这个依赖，用于验证管理员权限

from app.schemas.user_schema import UserRead

router = APIRouter(prefix="/api/v1/admin", tags=["Admin-User-Manager"])

# 响应模型（为了演示，这里直接使用User模型，实际生产建议创建 UserPublic Schema）
# from app.schemas.user import UserPublic, UserUpdate

@router.get("/users", response_model=List[User])
def read_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
    skip: int = 0,
    limit: int = 100,
    keyword: Optional[str] = Query(None, description="搜索用户名或姓名")
):
    """
    获取用户列表（支持搜索和分页）
    """
    statement = select(User).offset(skip).limit(limit).order_by(User.id.desc())
    
    if keyword:
        # 模糊搜索 username 或 full_name
        search = f"%{keyword}%"
        statement = statement.where(
            (User.username.contains(search)) | (User.full_name.contains(search))
        )
        
    result = db.execute(statement)
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=UserRead)
def get_user_detail(user_id: int, session: Session = Depends(get_db)):
    """
    获取单个用户详情
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 如果需要计算 role_label，可以在这里处理，或者在 Schema 中处理
    return user

@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    更新用户状态（封禁/正常）
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"msg": "状态更新成功", "data": user}

@router.put("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    重置用户密码（这里简单重置为 '123456'，实际请根据需求调整）
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 假设默认密码是 123456，请引入你的加密工具
    default_password = "123456"
    user.password = get_password_hash(default_password)
    
    db.add(user)
    db.commit()
    return {"msg": f"密码已重置为: {default_password}"}

@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_admin)
):
    """
    删除用户
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    db.delete(user)
    db.commit()
    return {"msg": "删除成功"}