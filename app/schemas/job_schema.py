from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime


# ====================
# 职位 (Job) 相关模型
# ====================

class JobBase(SQLModel):
    """职位基础字段（用于创建、更新和作为读取的基础）
    
    新增字段：
    - location: 工作地点
    - experience_requirement: 经验要求
    - education_requirement: 学历要求
    """
    title: str = Field(..., description="职位名称")
    job_id: Optional[str] = Field(None, description="职位编号")
    company: str = Field(..., description="公司名称")
    
    # 薪资范围
    salary: Optional[str] = Field(None, description="薪资范围") 
    
    # --- 新增的三个字段 ---
    location: Optional[str] = Field(None, description="工作地点，例如：东莞")
    experience_requirement: Optional[str] = Field(None, description="经验要求，例如：3-5年")
    education_requirement: Optional[str] = Field(None, description="学历要求，例如：本科")
    
    # 技能标签列表
    required_skills: Optional[List[str]] = Field(default_factory=list, description="技能标签列表")
    
    # 描述字段
    description: Optional[str] = Field(None, description="职位详情描述")


class JobRead(JobBase):
    """读取职位时返回的字段（包含ID、路径和时间戳）"""
    id: int
    pdf_path: Optional[str] = Field(None, description="PDF文件存储路径")
    created_at: datetime
    updated_at: datetime


class JobCreate(JobBase):
    """创建职位时的请求体模型"""
    # 如果需要强制某些字段在创建时必须存在，可以在这里重新定义
    # 目前直接继承 JobBase，所有字段均为可选（除了 title/company）
    pass


# ====================
# 新增：LLM 解析响应模型
# ====================

class JobParseResponse(SQLModel):
    """定义 /admin/jobs/parse 接口的响应模型。
    
    注意：
    1. 这里的字段名最好与 JobBase 保持一致，以便前端直接复用类型。
    2. 包含了新增的三个字段，确保 LLM 解析后能正确返回。
    """
    title: str
    company: str
    salary: str
    location: Optional[str] = Field(None, description="工作地点")
    experience_requirement: Optional[str] = Field(None, description="经验要求")
    education_requirement: Optional[str] = Field(None, description="学历要求")
    required_skills: List[str]
    description: str


# ====================
# 用户 (User) 相关模型
# ====================

class UserBase(SQLModel):
    """用户基础字段"""
    username: str = Field(..., index=True, description="用户名")
    email: Optional[str] = Field(None, index=True, description="邮箱")
    is_active: Optional[bool] = Field(True, description="是否激活")
    is_admin: Optional[bool] = Field(False, description="是否管理员")


class UserCreate(UserBase):
    """创建用户（包含密码）"""
    password: str = Field(..., description="密码")


class UserRead(UserBase):
    """返回用户信息（不包含密码）"""
    id: int


class UserDB(UserBase):
    """数据库模型（包含密码哈希）"""
    id: int
    hashed_password: str