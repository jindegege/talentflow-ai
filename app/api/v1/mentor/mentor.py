# routers/mentor.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func
from app.models.task import Task
from app.models.application import Application
from app.models.user import User
from app.schemas.dashboard import DashboardStats, ActivityList
from app.models.database import get_db

router = APIRouter(prefix="/api/v1/mentor")

# --- 接口 1: 顶部统计卡片 ---
@router.get("/dashboard/stats", response_model=DashboardStats)
def get_mentor_stats(db: Session = Depends(get_db)):
    # 1. 任务总数
    statement_total = select(func.count(Task.id))
    total_tasks = db.execute(statement_total).scalar_one()
    
    # 2. 进行中 (status = 1)
    statement_progress = select(func.count(Task.id)).where(Task.status == 1)
    in_progress = db.execute(statement_progress).scalar_one()
    
    # 3. 已完成 (status = 3)
    statement_completed = select(func.count(Task.id)).where(Task.status == 3)
    completed = db.execute(statement_completed).scalar_one()
    
    # 4. 待审核简历
    statement_pending = select(func.count(Application.id)).where(Application.status == "pending")
    pending_review = db.execute(statement_pending).scalar_one()

    return DashboardStats(
        total_tasks=total_tasks,
        in_progress=in_progress,
        pending_review=pending_review,
        completed=completed
    )

# --- 接口 2: 近期任务动态 (Timeline) ---
@router.get("/dashboard/activities", response_model=ActivityList)
def get_recent_activities(db: Session = Depends(get_db)):
    activities = []

    # 步骤 A: 获取最新的任务动态
    statement_tasks = select(Task).order_by(Task.updated_at.desc()).limit(20)
    tasks = db.execute(statement_tasks).scalars().all()

    for task in tasks:
        status_text = ""
        if task.status == 1: 
            status_text = "状态变更为“进行中”"
        elif task.status == 3: 
            status_text = "状态变更为“已完成”"
        
        if status_text:
            activities.append({
                "date": task.updated_at.strftime("%Y-%m-%d"),
                "title": f"{task.title}",
                "description": status_text,
                "type": "task"
            })

    # 步骤 B: 获取最新的投递动态
    # 关联查询 User 表
    statement_apps = (
        select(Application, User)
        .join(User, Application.user_id == User.id)
        .where(Application.status == "pending")
        .order_by(Application.created_at.desc())
        .limit(20)
    )
    # 这里的 result 是一个包含 (Application对象, User对象) 元组的迭代器
    app_results = db.execute(statement_apps).all()

    for app, user in app_results:
        # 获取对应的任务对象
        statement_task = select(Task).where(Task.id == app.task_id)
        task = db.execute(statement_task).scalar_one_or_none()
        
        if task:
            activities.append({
                "date": app.created_at.strftime("%Y-%m-%d"),
                "title": f"{task.title}",
                "description": f"用户 {user.full_name or user.username} 提交了新投递",
                "type": "application"
            })

    # 步骤 C: 合并并排序
    activities.sort(key=lambda x: x["date"], reverse=True)

    return ActivityList(activities=activities[:10])