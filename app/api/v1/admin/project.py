from fastapi import APIRouter, Depends
from sqlalchemy import func  # 1. 使用 SQLAlchemy 原生的 func
from sqlmodel import select
from datetime import datetime, timedelta
from typing import List, Dict

# 导入数据库会话和模型
from app.models.database import get_db, Session
from app.models.base import UserDB
from app.models.job_position import JobPosition
from app.models.resume import Resume

router = APIRouter(prefix="/api/v1/admin/stats", tags=["数据统计"])

@router.get("/overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    """
    获取首页关键指标卡片数据
    """
    # 1. 统计用户总数
    user_count = db.execute(select(func.count(UserDB.id))).scalars().one()
    
    # 2. 统计职位总数
    job_count = db.execute(select(func.count(JobPosition.id))).scalars().one()
    
    # 3. 统计简历总数
    resume_count = db.execute(select(func.count(Resume.id))).scalars().one()
    
    # 4. 统计待审核简历数
    pending_resume_count = db.execute(
        select(func.count(Resume.id)).where(Resume.status == 'pending')
    ).scalars().one()

    return {
        "users": user_count,
        "jobs": job_count,
        "resumes": resume_count,
        "pending_resumes": pending_resume_count
    }

@router.get("/resume-trend")
def get_resume_trend(days: int = 7, db: Session = Depends(get_db)):
    """
    获取简历增长趋势数据（用于折线图）
    """
    # 计算开始时间
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # 按日期分组统计
    query = (
        select(
            func.date(Resume.created_at).label("date"), 
            func.count(Resume.id).label("count")
        )
        .where(Resume.created_at >= start_date)
        .group_by(func.date(Resume.created_at))
        .order_by(func.date(Resume.created_at))
    )
    
    # 执行查询并获取所有结果
    results = db.execute(query).all()
    
    # 格式化数据供前端使用
    chart_data = []
    for row in results:
        chart_data.append({
            "date": str(row.date),
            "count": row.count
        })
        
    return chart_data

@router.get("/job-distribution")
def get_job_distribution(db: Session = Depends(get_db)):
    """
    获取职位状态占比（用于饼图）
    """
    query = (
        select(JobPosition.is_active, func.count(JobPosition.id))
        .group_by(JobPosition.is_active)
    )
    
    # 获取所有分组结果
    results = db.execute(query).all()
    
    chart_data = []
    for is_active, count in results:
        # 将布尔值或状态转换为前端易读的文字
        status_name = "已启用" if is_active else "已停用"
        chart_data.append({
            "name": status_name,
            "value": count
        })
        
    return chart_data