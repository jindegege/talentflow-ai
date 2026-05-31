from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional, List
from sqlalchemy import JSON, Column

class JobPosition(SQLModel, table=True):
    __tablename__ = "job_positions"
     
    id: Optional[int] = Field(default=None, primary_key=True)
      # --- 修改处：改为可选字段 ---
    job_id: Optional[str] = Field(
        default=None, 
        description="职位编号(可选，用于外部系统关联)"
    )
    title: str = Field(description="职位名称")
    company: str = Field(description="公司名称")
    salary: Optional[str] = Field(default=None, description="薪资范围")
    
    # --- 新增的三个字段 ---
    
    location: Optional[str] = Field(
        default=None, 
        description="工作地点，例如：东莞"
    )
    
    experience_requirement: Optional[str] = Field(
        default=None, 
        description="经验要求，例如：3-5年"
    )
    
    education_requirement: Optional[str] = Field(
        default=None, 
        description="学历要求，例如：本科"
    )
    
    # ----------------------

    # 职位要求的硬技能
    required_skills: List[str] = Field(
        default=[], 
        sa_column=Column(JSON), 
        description="职位要求技能列表"
    )
    
    description: str = Field(description="职位详细描述（用于向量化）")
    
    is_active: str = Field(description="是否发布")
    
    # --- 时间戳 ---
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")