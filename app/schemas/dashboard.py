# schemas/dashboard.py
from pydantic import BaseModel
from typing import List, Optional

class DashboardStats(BaseModel):
    total_tasks: int
    in_progress: int
    pending_review: int
    completed: int

class ActivityItem(BaseModel):
    date: str           # 日期，如 "2026-05-03"
    title: str          # 主标题，如 "前端开发任务"
    description: str    # 副标题，如 "状态变更为'进行中'" 或 "用户 张三 已接单"
    type: str           # 标记类型，前端可能用来显示不同图标 (task 或 application)

class ActivityList(BaseModel):
    activities: List[ActivityItem]