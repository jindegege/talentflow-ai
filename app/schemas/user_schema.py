from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

# ==========================================
# 1. 基础共享属性 (Shared Properties)
# ==========================================
class UserBase(BaseModel):
    """用户基础信息，用于创建和更新"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="电子邮箱")
    role: Optional[int] = Field(default=0, description="角色: 0=候选人, 1=管理员, 2=hr")

# ==========================================
# 2. 创建用户 (Create)
# ==========================================
class UserCreate(UserBase):
    """注册/创建用户时所需的数据"""
    password: str = Field(..., min_length=6, max_length=128, description="登录密码")

# ==========================================
# 3. 更新用户 (Update)
# ==========================================
class UserUpdate(BaseModel):
    """更新用户信息时所需的数据 (密码可选)"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    role: Optional[int] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128) # 仅在修改密码时填写

# ==========================================
# 4. 数据库模型响应 (DB Model)
# ==========================================
class UserDB(UserBase):
    """数据库模型，包含ID和密码"""
    id: int
    password: str  # 注意：实际返回时通常应该隐藏密码，但在内部处理时需要
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        
# ==========================================
# 5. 公共响应模型 (Public Response)
# ==========================================

class UserRead(BaseModel):
    """API 返回给前端的用户信息 (不包含密码)"""
    id: int
    username: str
    email: str
    role: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # 新增字段：对应数据库的 full_name 和 is_active
    full_name: Optional[str] = None
    is_active: bool = True

    # 新增字段：用于前端显示 "管理员" 或 "求职者"
    # 注意：这个字段不是数据库字段，是计算出来的
    role_label: Optional[str] = None

    class Config:
        from_attributes = True

# 修改 UserOut：
# 1. 不再继承 UserBase，避免继承 email 等必填字段
# 2. 只定义登录返回需要的字段
class UserOut(BaseModel):
    id: int
    username: str       # 加上 username，通常登录都要返回用户名
    
    # 如果你确实需要返回 email，请设为可选
    # email: Optional[str] = None 
    role: Optional[int] = 0

    class Config:
        from_attributes = True

# ==========================================
# 6. 登录响应 (Auth)
# ==========================================
class Token(BaseModel):
    """登录成功后的 Token 响应"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """用于解析 Token 内部数据的类"""
    username: Optional[str] = None
    

# ==========================================
# 登录返回结构 (Login Response Schema)
# ==========================================

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut