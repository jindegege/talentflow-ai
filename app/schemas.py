from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ==========================================
# 租户模型 (Tenant Schemas)
# 用于处理公司/组织信息
# ==========================================

class TenantBase(BaseModel):
    name: str

class TenantCreate(TenantBase):
    pass

class TenantOut(TenantBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True  # 适用于 SQLAlchemy 2.0+ (原 orm_mode)

# ==========================================
# 用户模型 (User Schemas)
# ==========================================

class UserBase(BaseModel):
    username: str
    is_active: Optional[bool] = True
    role: Optional[int] = 0
    # 注意：在 Base 中 tenant_id 是可选的，方便用于查询结果等场景
    tenant_id: Optional[int] = None

class UserCreate(UserBase):
    # 关键修改：注册时密码必须提供
    password: str
    # 关键修改：注册时 tenant_id 必须是整数 (int)，不能是 None
    # 这会强制前端在注册时必须传 tenant_id
    tenant_id: int

class UserOut(UserBase):
    id: int
    nickname: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ==========================================
# 登录返回结构 (Login Response Schema)
# ==========================================

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut
    
    
# --- 发送消息的请求格式 ---
class ChatRequest(BaseModel):
    message: str
    session_id: int = None # 允许为空，为空则新建
    

# --- 会话相关 ---
class ChatSessionBase(BaseModel):
    title: str
    created_at: datetime

class ChatSessionResponse(ChatSessionBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True

# --- 消息相关 ---
class ChatMessageBase(BaseModel):
    role: str
    content: str

class ChatMessageResponse(ChatMessageBase):
    id: int
    session_id: int
    created_at: datetime

    class Config:
        orm_mode = True