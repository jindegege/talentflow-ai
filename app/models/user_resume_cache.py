from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

# =================================================================
# 1. 缓存表模型 (新增)
# =================================================================
class UserResumeCache(SQLModel, table=True):
    """
    用户简历缓存表
    用于记录：用户 + 职位 -> 优化简历ID 的映射关系
    """
    __tablename__ = "user_resume_cache"

    # --- 字段定义 ---
    id: Optional[int] = Field(default=None, primary_key=True, description="主键ID")
    
    user_id: int = Field(index=True, nullable=False, description="用户ID")
    
    job_id: str = Field(index=True, nullable=False, description="职位ID")
    
    optimized_resume_id: int = Field(nullable=False, description="优化后的简历ID")
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow}, description="更新时间")
