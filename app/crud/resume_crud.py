from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import base
from app.schemas import resume_schema

# ==========================================
# 1. 创建简历
# ==========================================
def create_resume(db: Session, user_id: int, resume_in: resume_schema.ResumeCreate):
    """
    上传/创建新简历
    """
    db_resume = base.ResumeDB(
        user_id=user_id,
        title=resume_in.title,
        summary=resume_in.summary,
        project_experience=resume_in.project_experience,
        education=resume_in.education,
        is_default=resume_in.is_default
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    return db_resume

# ==========================================
# 2. 获取用户简历列表
# ==========================================
def get_user_resumes(db: Session, user_id: int):
    """
    获取当前用户的所有简历
    """
    return db.query(base.ResumeDB)\
             .filter(base.ResumeDB.user_id == user_id)\
             .all()

# ==========================================
# 3. 获取简历详情
# ==========================================
def get_resume(db: Session, resume_id: int, user_id: int):
    """
    获取单个简历详情（增加权限校验，只能查自己的）
    """
    return db.query(base.ResumeDB)\
             .filter(base.ResumeDB.id == resume_id)\
             .filter(base.ResumeDB.user_id == user_id)\
             .first()

# ==========================================
# 4. 更新简历
# ==========================================
def update_resume(db: Session, resume_id: int, user_id: int, resume_in: resume_schema.ResumeUpdate):
    """
    更新简历内容
    """
    db_resume = get_resume(db, resume_id, user_id)
    if db_resume:
        # 更新字段
        db_resume.title = resume_in.title
        db_resume.summary = resume_in.summary
        db_resume.project_experience = resume_in.project_experience
        db_resume.education = resume_in.education
        # 可以在这里添加 AI 自动润色后的字段更新
        
        db.commit()
        db.refresh(db_resume)
    return db_resume

# ==========================================
# 5. 删除简历
# ==========================================
def delete_resume(db: Session, resume_id: int, user_id: int):
    """
    删除简历
    """
    db_resume = get_resume(db, resume_id, user_id)
    if db_resume:
        db.delete(db_resume)
        db.commit()
        return True
    return False

# ==========================================
# 6. 设置默认简历
# ==========================================
def set_default_resume(db: Session, user_id: int, resume_id: int):
    """
    设置某份简历为默认简历
    """
    # 1. 先取消该用户所有简历的默认状态
    db.query(base.ResumeDB)\
      .filter(base.ResumeDB.user_id == user_id)\
      .update({"is_default": False})
    
    # 2. 设置新的默认简历
    db_resume = db.query(base.ResumeDB)\
                  .filter(base.ResumeDB.id == resume_id)\
                  .filter(base.ResumeDB.user_id == user_id)\
                  .first()
    if db_resume:
        db_resume.is_default = True
        db.commit()
        return db_resume
    return None