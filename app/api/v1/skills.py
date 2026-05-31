# 技能图谱，用于获取标准化的技能标签，供前端下拉框使用。
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.models import base,database

router = APIRouter(prefix="/api/v1/skills", tags=["技能图谱"])

@router.get("", response_model=List[dict])
def get_skills(
    db: Session = Depends(database.get_db)
):
    """获取所有技能标签"""
    skills = db.query(base.SkillDB).all()
    return [{"id": s.id, "name": s.name, "category": s.category} for s in skills]