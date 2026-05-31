# app/schemas.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- 职位 ---
class JobBase(BaseModel):
    title: str
    company: str
    description: str
    location: Optional[str] = None
    salary_range: Optional[str] = None

class JobOut(JobBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- 投递 ---
class ApplicationBase(BaseModel):
    resume_id: int  # 投递时必须指定使用哪份简历

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationOut(ApplicationBase):
    id: int
    user_id: int
    job_id: int
    cover_letter: str
    status: str
    applied_at: datetime
    
    class Config:
        from_attributes = True