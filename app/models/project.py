from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.dialects.mysql import JSON as MySQLJSON 

class Project(SQLModel, table=True):
    __tablename__ = "projects"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, description="任务标题")
    description: str = Field(description="任务详细描述")
    category: str = Field(description="分类，如 前端、后端、设计")
    price: int = Field(description="赏金，单位：分或元")
    difficulty: Optional[str] = Field(default="中级", description="难度等级")
    duration: int = Field(description="截止天数")

    skills: List[str] = Field(
        default_factory=list, 
        sa_column=Column("skills", MySQLJSON, nullable=False)
    )
   
    
    status: str = Field(default="open", description="任务状态")
    taken_by: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
