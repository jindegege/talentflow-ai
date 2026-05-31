# app/api/v1/recommend.py (AI 推荐)
# 这是“驾驶舱”的核心，结合简历和职位向量进行匹配。
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas import job_schema
from app.models import base,database
from app.core import deps

router = APIRouter(prefix="/api/v1/recommend", tags=["AI 推荐"])

@router.get("/jobs", response_model=List[job_schema.JobRead])
def recommend_jobs(
    resume_id: int,
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    基于简历的 AI 职位推荐
    1. 获取简历向量
    2. 在向量库中检索相似职位
    3. 返回匹配度最高的 Top 5
    """
    # 1. 校验简历归属
    resume = db.query(base.ResumeDB).filter(
        base.ResumeDB.id == resume_id,
        base.ResumeDB.user_id == current_user.id
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    # 2. 模拟向量检索 (实际应调用 Milvus/Chroma)
    # matched_jobs = vector_db.search(resume.vector_id)
    matched_jobs = db.query(base.JobDB).limit(5).all()
    
    return matched_jobs