from typing import Optional, List
from sqlmodel import SQLModel, Field
from datetime import datetime
# 引入 SQLAlchemy 的 Column 和 MySQL 的 JSON 类型
from sqlalchemy import Column
from sqlalchemy.dialects.mysql import JSON as MySQLJSON 

class Resume(SQLModel, table=True):
    __tablename__ = "resumes"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    name: Optional[str] = Field(default=None, max_length=50)
    phone: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=100)
    title: Optional[str] = Field(default=None, max_length=255)
    
    # 文本字段 (对应数据库的 TEXT / LONGTEXT)
    summary: Optional[str] = Field(default=None)
    education: Optional[str] = Field(default=None)
    # 注意：之前的 experience 字段已废弃，统一使用 work_experience
    work_experience: Optional[str] = Field(default=None)
    project_experience: Optional[str] = Field(default=None)
    
    # 技能标签 (使用 JSON 类型存储 List[str])
    skills: List[str] = Field(
        default_factory=list, 
        sa_column=Column("skills", MySQLJSON, nullable=False)
    )
    
    # 补充数据库表中存在但原代码缺失的字段
    source: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = Field(default="active", max_length=20)
    parse_status: int = Field(default=0)  # 0:未解析, 1:成功, 2:失败
    resume_language: Optional[str] = Field(default="zh-CN", max_length=10)
    
    target_job_id: Optional[str] = Field(default=None, max_length=100)
    vector_id: Optional[str] = Field(default=None, max_length=100)
    
    is_default: bool = Field(default=False)
    
    remark: Optional[str] = Field(default=None, max_length=255)
    
    # 时间戳字段
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)