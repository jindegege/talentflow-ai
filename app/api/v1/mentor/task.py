from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List, Optional

# 引入数据库会话、模型和 Pydantic 模式
from app.models.database import get_db
from app.models.task import Task
from app.models.user import User 
from app.schemas.task_schema import TaskCreate, TaskOut, TaskUpdate
from app.core.deps import get_current_active_user 

# 路由前缀设置为 /api/v1/mentor
router = APIRouter(prefix="/api/v1/mentor", tags=["任务管理"])

# --- 接口 1: 发布新任务 ---
@router.post("/tasks", response_model=TaskOut, summary="发布新任务")
def create_task(
    *,
    db: Session = Depends(get_db),
    task_in: TaskCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    发布一个新任务，自动关联当前登录用户为 mentor_id
    """
    task_in.mentor_id = current_user.id 
    
    # 将 Pydantic 模型转为 SQLModel 实例并存入数据库
    db_task = Task.from_orm(task_in) # 或者 Task(**task.dict())
    # 将 Pydantic 模型转换为 SQLModel，并强制注入 mentor_id
    db_task = Task.model_validate(task_in, update={"mentor_id": current_user.id})
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return db_task

# --- 接口 2: 获取任务列表 ---
@router.get("/tasks", response_model=List[TaskOut], summary="获取我的任务列表")
def read_tasks(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[int] = Query(None, description="筛选状态：0-待审核, 1-进行中..."),
    current_user: User = Depends(get_current_active_user)
):
    """
    获取当前导师发布的任务列表，支持分页和状态筛选
    """
    # 1. 构建基础查询
    statement = select(Task).where(Task.mentor_id == current_user.id)
    
    # 2. 筛选状态
    if status is not None:
        statement = statement.where(Task.status == status)
        
    # 3. 排序（最新的在前面）
    statement = statement.order_by(Task.created_at.desc())
    
    # 4. 分页
    statement = statement.offset(skip).limit(limit)
    
    # 5. 执行
    results = db.execute(statement).all()
    
    # 解包元组 (因为 execute().all() 返回的是 [(obj,), ...])
    return [task for (task,) in results]

# --- 接口 3: 获取单个任务详情 ---
@router.get("/tasks/{task_id}", response_model=TaskOut, summary="任务详情")
def get_task_detail(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    获取单个任务的详细信息
    """
    statement = select(Task).where(Task.id == task_id)
    db_task = db.execute(statement).scalar_one_or_none()
    
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")
        
    # 安全校验：确保只能查看自己发布的任务（可选，视业务需求而定）
    # if db_task.mentor_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="无权查看此任务")
        
    return db_task

# --- 接口 4: 更新任务 ---
@router.put("/tasks/{task_id}", response_model=TaskOut, summary="更新任务")
def update_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    更新任务信息（如修改状态、编辑描述等）
    """
    statement = select(Task).where(Task.id == task_id)
    db_task = db.execute(statement).scalar_one_or_none()
    
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")
        
    # 权限检查：只有发布者才能修改
    if db_task.mentor_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此任务")
    
    # 更新逻辑：exclude_unset=True 表示只更新传入的字段
    task_data = task_in.model_dump(exclude_unset=True)
    db_task.sqlmodel_update(task_data)
    
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return db_task

# --- 接口 5: 删除任务 ---
@router.delete("/tasks/{task_id}", status_code=204, summary="删除任务")
def delete_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """
    删除一个任务
    """
    statement = select(Task).where(Task.id == task_id)
    db_task = db.execute(statement).scalar_one_or_none()
    
    if not db_task:
        raise HTTPException(status_code=404, detail="任务不存在")
        
    if db_task.mentor_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此任务")
        
    db.delete(db_task)
    db.commit()
    
    return None