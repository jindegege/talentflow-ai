# app/services/recommendation.py
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.celery_app import celery_app # 保持 Celery 引用，用于异步触发
from app.rag.recommendation_service import generate_recommendation_task as sync_task

# --- 方案A：直接调用（适合 MCP 实时获取结果）---
def get_recommendations_sync(user_id: int, top_k: int = 5) -> Dict[str, Any]:
    """
    同步获取推荐结果。
    注意：这是一个耗时操作，直接调用会阻塞。
    """
    try:
        # 直接执行同步逻辑（假设 sync_task 是你的核心逻辑函数）
        # 如果 generate_recommendation_task 是纯逻辑，直接调用它
        result = sync_task(user_id, top_k) 
        return result
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# --- 方案B：异步触发（适合 MCP 仅返回任务ID）---
# def trigger_recommendations_async(user_id: int, top_k: int = 5) -> Dict[str, Any]:
#     """
#     异步触发推荐任务。
#     返回任务ID，前端可轮询结果。
#     """
#     task = sync_task.delay(user_id, top_k)
#     return {"status": "processing", "task_id": task.id}