from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from app.models import base
from app.schemas import job_schema # 假设你有对应的 Pydantic 模型

# ==========================================
# 1. 创建职位
# ==========================================
def create_job(db: Session, job_in: job_schema.JobCreate):
    """
    创建新职位
    """
    db_job = base.JobDB(
        title=job_in.title,
        company=job_in.company,
        description=job_in.description,
        location=job_in.location,
        salary_range=job_in.salary_range,
        source_url=job_in.source_url
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

# ==========================================
# 2. 查询职位列表
# ==========================================
def get_jobs(db: Session,skip: int = 0, limit: int = 100):
    """
    获取当前租户下的职位列表
    """
    return db.query(base.JobDB)\
             .offset(skip)\
             .limit(limit)\
             .all()

# ==========================================
# 3. 搜索职位 (核心功能)
# ==========================================
def search_jobs(db: Session, keyword: str):
    """
    根据关键词搜索职位 (标题或描述)
    """
    # 构建模糊查询
    search_filter = f"%{keyword}%"
    
    return db.query(base.JobDB)\
             .filter(
                 or_(
                     base.JobDB.title.contains(search_filter),
                     base.JobDB.description.contains(search_filter)
                 )
             )\
             .all()

# ==========================================
# 4. 获取单个职位
# ==========================================
def get_job(db: Session, job_id: int):
    """
    获取单个职位详情
    """
    return db.query(base.JobDB)\
             .filter(base.JobDB.id == job_id)\
             .first()

# ==========================================
# 5. 删除职位
# ==========================================
def delete_job(db: Session, job_id: int):
    """
    删除职位
    """
    db_job = get_job(db, job_id)
    if db_job:
        db.delete(db_job)
        db.commit()
        return True
    return False