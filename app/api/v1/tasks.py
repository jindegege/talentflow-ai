# 用于实战工作台，学生在这里领取任务、提交交付物

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.schemas import task_schema
from app.models import base,database
from app.core import deps

router = APIRouter(prefix="/api/v1/tasks", tags=["实战任务"])

@router.get("", response_model=List[task_schema.TaskOut])
def list_tasks(
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """获取任务列表"""
    tasks = db.query(base.TaskDB).all()
    return tasks

@router.post("/{task_id}/submit", response_model=task_schema.TaskDeliveryOut)
def submit_task(
    task_id: int,
    delivery_in: task_schema.TaskDeliveryCreate,
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    """提交任务交付物"""
    # 校验任务存在
    task = db.query(base.TaskDB).filter(base.TaskDB.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 创建交付记录
    db_delivery = base.TaskDeliveryDB(
        task_id=task_id,
        user_id=current_user.id,
        delivery_url=delivery_in.delivery_url,
        comment=delivery_in.comment
    )
    db.add(db_delivery)
    db.commit()
    db.refresh(db_delivery)
    return db_delivery