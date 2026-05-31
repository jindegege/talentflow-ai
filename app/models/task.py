from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column, Text
from sqlalchemy.dialects.mysql import JSON as MySQLJSON 

class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 基础信息
    title: str = Field(index=True, description="任务标题")
    description: str = Field(sa_column=Column(Text), description="任务详细描述")
    category: str = Field(index=True, description="分类，如 前端、后端、设计")
    
    # 薪酬与难度
    price: int = Field(description="赏金，单位：分") 
    difficulty: Optional[str] = Field(default="中级", description="难度等级")
    duration: int = Field(description="截止天数（天）")

    # JSON字段：技能标签
    skills: List[str] = Field(
        default_factory=list, 
        sa_column=Column("skills", MySQLJSON, nullable=False)
    )
   
    # 状态管理
    status: int = Field(default=0, description="0-待审核, 1-进行中, 2-已暂停, 3-已完成, 4-已驳回")
    
    # --- 外键关联 ---
    # 1. 接单者 (Freelancer)
    taken_by: Optional[int] = Field(default=None, foreign_key="users.id", description="接单者ID")
    
    # 2. 发布者 (Mentor)
    mentor_id: int = Field(foreign_key="users.id", description="发布者ID")
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # --- 关系定义 (核心修复：用 sa_relationship_kwargs 消除歧义) ---
    
    # 1. 发布者关系
    mentor: Optional["User"] = Relationship(
        back_populates="tasks", 
        sa_relationship_kwargs={"foreign_keys": "[Task.mentor_id]"}
    )
    
    # 2. 接单者关系
    taker: Optional["User"] = Relationship(
        back_populates="accepted_tasks",
        sa_relationship_kwargs={"foreign_keys": "[Task.taken_by]"}
    )

    # 3. 任务对应的投递记录
    applications: List["Application"] = Relationship(back_populates="task")