# 这是用户管理自己简历的核心接口，支持多份简历的增删改查，以及 AI 辅助生成
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas import resume_schema
from app.models import base,database
from app.core import deps

router = APIRouter(prefix="/api/v1/resume", tags=["简历管理"])

# ==========================================
# 简历 CRUD
# ==========================================

@router.get("/list", response_model=List[resume_schema.ResumeRead])
def get_my_resumes(
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """获取当前用户的所有简历"""
    resumes = db.query(base.ResumeDB).filter(base.ResumeDB.user_id == current_user.id).all()
    return resumes

@router.post("", response_model=resume_schema.ResumeCreate)
def create_resume(
    resume_in: resume_schema.ResumeCreate,
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """创建新简历"""
    db_resume = base.ResumeDB(
        user_id=current_user.id,
        title=resume_in.title,
        summary=resume_in.summary,
        project_experience=resume_in.project_experience,
        education=resume_in.education
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    return db_resume

@router.put("/{resume_id}", response_model=resume_schema.ResumeRead)
def update_resume(
    resume_id: int,
    resume_in: resume_schema.ResumeUpdate,
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """更新简历"""
    # 1. 查找并校验归属
    db_resume = db.query(base.ResumeDB).filter(
        base.ResumeDB.id == resume_id,
        base.ResumeDB.user_id == current_user.id
    ).first()
    
    if not db_resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    # 2. 更新字段
    update_data = resume_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_resume, key, value)

    db.commit()
    db.refresh(db_resume)
    return db_resume

@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int,
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """删除简历"""
    db_resume = db.query(base.ResumeDB).filter(
        base.ResumeDB.id == resume_id,
        base.ResumeDB.user_id == current_user.id
    ).first()
    
    if not db_resume:
        raise HTTPException(status_code=404, detail="简历不存在")
        
    db.delete(db_resume)
    db.commit()
    return {"message": "删除成功"}

# ==========================================
# AI 辅助功能
# ==========================================

@router.post("/{resume_id}/optimize", response_model=resume_schema.ResumeRead)
def optimize_resume(
    resume_id: int,
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    AI 润色简历
    调用 LLM 优化项目经历描述
    """
    # 1. 获取简历
    db_resume = db.query(base.ResumeDB).filter(
        base.ResumeDB.id == resume_id,
        base.ResumeDB.user_id == current_user.id
    ).first()
    if not db_resume:
        raise HTTPException(status_code=404, detail="简历不存在")

    # 2. 调用 AI (模拟)
    # optimized_text = await ai_service.polish_text(db_resume.project_experience)
    optimized_text = f"[AI 优化后] {db_resume.project_experience}... (使用了 STAR 法则)"
    
    db_resume.project_experience = optimized_text
    db.commit()
    db.refresh(db_resume)
    return db_resume