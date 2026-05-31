# 该模块实现了求职驾驶舱的核心业务逻辑，包括职位查询（列表、详情）和智能投递（申请职位）
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

# 导入本地模块
from app.schemas import job_schema,application_schema
from app.models import base,database
from app.core import deps

router = APIRouter(prefix="/api/v1/jobs", tags=["职位与投递"])

# ==========================================
# 职位查询接口
# ==========================================

@router.get("", response_model=List[job_schema.JobRead])
def search_jobs(
    q: Optional[str] = Query(None, description="搜索关键词 (职位名称/公司)"),
    location: Optional[str] = Query(None, description="工作地点筛选"),
    skip: int = 0,
    limit: int = 20,
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    获取职位列表
    支持关键词搜索和地点筛选
    """
    # 构建查询
    query = db.query(base.JobDB)
    
    # 关键词搜索
    if q:
        query = query.filter(base.JobDB.title.contains(q) | base.JobDB.company.contains(q))
    
    # 地点筛选
    if location:
        query = query.filter(base.JobDB.location == location)
    
    # 分页
    jobs = query.offset(skip).limit(limit).all()
    return jobs

@router.get("/{job_id}", response_model=job_schema.JobRead)
def get_job_detail(
    job_id: int,
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    获取职位详情
    """
    job = db.query(base.JobDB).filter(
        base.JobDB.id == job_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="职位不存在")
    
    return job

# ==========================================
# 智能投递接口
# ==========================================

@router.post("/{job_id}/apply", response_model=application_schema.ApplicationOut)
def apply_for_job(
    job_id: int,
    application_in: application_schema.ApplicationCreate,
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    智能投递职位
    1. 校验职位是否存在
    2. 校验简历是否属于当前用户
    3. 调用 AI 生成求职信
    4. 创建投递记录
    """
    # 1. 校验职位
    job = db.query(base.JobDB).filter(
        base.JobDB.id == job_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="职位不存在")

    # 2. 校验简历归属
    resume = db.query(base.ResumeDB).filter(
        base.ResumeDB.id == application_in.resume_id,
        base.ResumeDB.user_id == current_user.id
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在或无权使用")

    # 3. 调用 AI 生成求职信 (模拟)
    # TODO: 这里接入 LangGraph/MCP 服务
    # cover_letter = await ai_service.generate_cover_letter(resume, job)
    cover_letter = f"尊敬的招聘经理：\n\n我对贵公司的 {job.title} 职位非常感兴趣。基于我的简历（{resume.title}），我相信我能胜任这份工作。"

    # 4. 创建投递记录
    db_application = base.ApplicationDB(
        user_id=current_user.id,
        job_id=job_id,
        resume_id=application_in.resume_id,
        cover_letter=cover_letter,
        status="applied"
    )
    
    db.add(db_application)
    db.commit()
    db.refresh(db_application)
    
    return db_application

# ==========================================
# 投递记录接口
# ==========================================

@router.get("/applications/my", response_model=List[application_schema.ApplicationOut])
def get_my_applications(
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """
    获取当前用户的投递记录
    """
    applications = db.query(base.ApplicationDB)\
                     .filter(base.ApplicationDB.user_id == current_user.id)\
                     .order_by(base.ApplicationDB.applied_at.desc())\
                     .all()
    return applications