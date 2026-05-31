from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from typing import Optional
from datetime import datetime

from .user import User
from .task import Task

class Application(SQLModel, table=True):
    """
    投递记录模型
    """
    __tablename__ = "applications"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    user_id: int = Field(
        default=None, 
        index=True, 
        description="关联用户ID",
        foreign_key="users.id"
    )
    
    # 关键修复点：
    # 1. 确保类型是 String (如果 job_positions.job_id 是字符串)
    # 2. 显式声明 ForeignKey 字符串
    job_id: Optional[str] = Field(
        default=None, 
        index=True,  # 保留索引以提高查询速度
        description="关联职位的业务ID (对应 job_positions.job_id)"
    )
    
    # 同理，任务ID也需要外键关联
    task_id: Optional[int] = Field(
        default=None, 
        foreign_key="tasks.id", 
        index=True, 
        description="关联任务ID"
    )
    resume_id: Optional[int] = Field(
        default=None, 
        index=True, 
        description="使用的简历ID"
    )
    
    cover_letter: Optional[str] = Field(
        default=None, 
        sa_column=Column("cover_letter", Text, nullable=True), 
        description="AI生成的求职信"
    )

    status: Optional[str] = Field(
        default="pending", 
        sa_column=Column("status", String(20), nullable=True), 
        description="投递状态"
    )

    created_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column("created_at", DateTime, nullable=False)
    )
    
    updated_at: Optional[datetime] = Field(
        default_factory=datetime.utcnow,
        sa_column=Column("updated_at", DateTime, nullable=False)
    )
    
    # --- 关系定义 (可选，但推荐) ---
    # 这样你可以通过 application.owner 直接拿到用户对象
    owner: Optional[User] = Relationship(back_populates="applications")
    
    # 这样你可以通过 application.task 直接拿到任务对象
    task: Optional[Task] = Relationship() 