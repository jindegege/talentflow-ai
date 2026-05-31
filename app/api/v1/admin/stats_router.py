from fastapi import APIRouter, Depends
from sqlmodel import func, select
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
    user_count = db.execute(select(func.count(UserDB.id))).one()
    
    # 2. 统计职位总数
    job_count = db.execute(select(func.count(JobPosition.id))).one()
    
    # 3. 统计简历总数
    resume_count = db.execute(select(func.count(Resume.id))).one()
    
    # 4. 统计待审核简历数 (假设状态为 'pending' 表示待审核)
    pending_resume_count = db.execute(
        select(func.count(Resume.id)).where(Resume.status == 'pending')
    ).one()

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
    # 注意：这里使用了 SQL 的日期格式化函数，不同数据库语法可能不同（这里是 SQLite/MySQL 写法）
    # 如果使用 PostgreSQL，需要使用 func.to_char
    
    query = (
        select(
            func.date(Resume.created_at).label("date"), 
            func.count(Resume.id).label("count")
        )
        .where(Resume.created_at >= start_date)
        .group_by(func.date(Resume.created_at))
        .order_by(func.date(Resume.created_at))
    )
    
    results = db.execute(query).all()
    
    # 格式化数据供前端使用
    chart_data = []
    # 简单处理：确保每一天都有数据（即使为0），这里为了演示直接返回查询结果
    for row in results:
        chart_data.append({
            "date": str(row.date),
            "count": row.count
        })
        
    return chart_data

@router.get("/job-distribution")
def get_job_distribution(db: Session = Depends(get_db)):
    """
    获取职位分类占比（用于饼图）
    假设 JobPosition 表中有一个 category 字段，或者我们用 title 的关键词做简单分类
    """
    # 这里演示一个简单的逻辑：统计不同 status 的职位数量，或者如果有 category 字段则按 category 统计
    # 假设我们按 status 统计分布
    query = (
        select(JobPosition.is_active, func.count(JobPosition.id))
        .group_by(JobPosition.is_active)
    )
    
    results = db.execute(query).all()
    
    chart_data = []
    for is_active, count in results:
        chart_data.append({
            "name": is_active, # 比如 'active', 'closed'
            "value": count
        })
        
    return chart_data