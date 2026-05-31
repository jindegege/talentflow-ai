from sqlmodel import SQLModel, Field
from typing import Optional, List

from sqlalchemy import Column, JSON

class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, description="业务用户ID")
    name: Optional[str] = Field(default=None, description="用户姓名")
    
    expected_position: Optional[str] = Field(default=None, description="期望职位")
    
    profile_summary: Optional[str] = Field(default=None, description="个人简介/经历描述（用于向量化）")
    
    # 使用 JSON 存储技能列表，如 ["Vue", "Java", "MySQL"]
    skills: List[str] = Field(
        default=[], 
        sa_column=Column(JSON), 
        description="用户掌握的技能列表"
    )
    
    
    # bio: Optional[str] = Field(default=None, description="个人简介/经历描述（用于向量化）")

