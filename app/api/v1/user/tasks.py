from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlmodel import Session
from typing import List, Optional
from datetime import datetime

# 假设你的项目结构如下，请根据实际路径调整导入
from app.models.database import get_db
from app.models.task import Task
from app.schemas.task_schema import TaskOut
from app.core.deps import get_current_user
from app.models.user import User

# 创建路由对象
router = APIRouter(prefix="/api/v1/user", tags=["用户任务"])

# ---------------------------------------------------------
# 1. 获取实战任务列表 (GET /user/tasks/)
# 对应前端：实战任务大厅的卡片列表
# ---------------------------------------------------------
@router.get("/tasks", response_model=List[TaskOut])
async def get_task_list(
    *,
    category: Optional[str] = Query(None, description="任务分类筛选，如：前端、后端、设计"),
    # status: Optional[int] = Query(0, description="任务状态，默认 0"),
    skip: int = 0,
    limit: int = 100,
    db=Depends(get_db)
):
    """
    获取任务列表，支持按分类筛选
    """
    print(f"category --- {category}")
    # 构建查询语句
    stmt = select(Task)
    
    # 如果传递了分类参数，则进行过滤
    if category:
        stmt = stmt.where(Task.category == category)
        
    # 排序：按创建时间倒序
    stmt = stmt.order_by(Task.created_at.desc()).offset(skip).limit(limit)
    
    result = db.execute(stmt)
    tasks = result.scalars().all()
    
    return tasks

# ---------------------------------------------------------
# 2. 获取任务详情 (GET /user/tasks/{task_id})
# 对应前端：点击“立即接单”后弹出的详情或跳转的详情页
# ---------------------------------------------------------
@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task_detail(
    *,
    task_id: int,
    db=Depends(get_db)
):
    """
    获取单个任务的详细信息
    """
    # 使用 session.get 快捷方法
    task =  db.get(Task, task_id)  
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已被删除")   
        
    return task

@router.post("/tasks/{task_id}/apply")
async def apply_task(
    *,
    task_id: int, 
    current_user: User = Depends(get_current_user), # 获取当前登录用户
    db: Session = Depends(get_db)
):
    # 1. 查找任务
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
        
    # 2. 检查任务状态：必须是 active 且 没人接 (taken_by 是 None)
    if task.status != 1 or task.taken_by is not None:
        raise HTTPException(status_code=400, detail="任务已被接取，手慢无！")
    
    # 3. 执行接单逻辑
    task.taken_by = current_user.id   # 核心：绑定用户ID
    task.updated_at = datetime.now()  # 更新时间
    
    db.commit()
    db.refresh(task)
    
    return {"msg": "接单成功", "task": task}