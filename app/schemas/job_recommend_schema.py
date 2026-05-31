from pydantic import BaseModel
from typing import List

class JobRecommendationItem(BaseModel):
    job_id: int
    title: str
    company_name: str
    salary: str
    match_score: int  # 匹配度百分比，如 95
    matched_skills: List[str] # 命中的技能标签
    tags: List[str]   # 显示在底部的标签 (Vue3, TypeScript...)

class RecommendationResponse(BaseModel):
    user_id: int
    recommendations: List[JobRecommendationItem]