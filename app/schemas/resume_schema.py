from typing import Optional, List
from sqlmodel import SQLModel
from datetime import datetime

# --- 基础共享字段 ---
class ResumeBase(SQLModel):
    user_id: Optional[int] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    
    # 文本大字段
    summary: Optional[str] = None
    education: Optional[str] = None
    work_experience: Optional[str] = None
    project_experience: Optional[str] = None
    
    # 技能标签 (前端和后端交互时，保持为 List[str] 即可)
    skills: Optional[List[str]] = None
    
    # 补充之前遗漏的数据库字段
    source: Optional[str] = None          # 简历文件路径
    status: Optional[str] = "active"      # 简历状态
    parse_status: int = 0                 # 解析状态: 0-未解析, 1-成功, 2-失败
    resume_language: Optional[str] = "zh-CN" # 简历语言
    target_job_id: Optional[str] = None   # 关联的职位ID
    vector_id: Optional[str] = None       # 向量库ID
    is_default: int = 0

# --- 创建时的模型 ---
class ResumeCreate(ResumeBase):
    """
    创建简历时使用的模型
    """
    pass

# --- 更新时的模型 ---
class ResumeUpdate(ResumeBase):
    """
    更新简历时使用的模型
    所有字段默认都是可选的，方便局部更新
    """
    pass

# --- 读取时的模型 (响应给前端) ---
class ResumeRead(ResumeBase):
    """
    返回给前端的模型，包含数据库生成的字段
    """
    id: int
    created_at: datetime
    updated_at: datetime

    # 现代 SQLModel/Pydantic V2 推荐使用 model_config
    model_config = {"from_attributes": True}
    
  
class ResumeApplicationOut(SQLModel):
    id: int
    # 来自 User 表
    candidate_name: str
    experience_years: Optional[int] = None  # 假设这个字段在 Resume 表里
    # 来自 JobPosition 表
    job_title: str
    job_skills: Optional[str] = None
    # 来自 Resume 表
    applied_at: datetime
    status: str