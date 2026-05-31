# app/api/v1/user/job_recommendation.py

from fastapi import APIRouter, Depends, HTTPException
from app.models.database import get_db
from sqlmodel import Session
from app.rag.recommendation_service import RecommendationService
from app.rag.recommendation_service import generate_recommendation_task
from celery.result import AsyncResult
from app.core.celery_app import celery_app

from app.utils.logger import logger
from app.rag.chain import get_rag_chain

# 创建路由对象
router = APIRouter(prefix="/api/v1/user", tags=["职位推荐"])
    

from fastapi import Body
from typing import Dict, Any

from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env

from langsmith import traceable

# --- 修改点1: 改为 POST ---
@router.post("/recommend/submit")
@traceable(run_type="chain", name="recommend_api_call")
async def recommend_submit(user_id: int = Body(..., embed=True), top_k: int = Body(5)):
    """
    提交推荐任务
    生产环境建议使用 POST 防止缓存问题，并支持更复杂的参数结构
    """
    task = generate_recommendation_task.delay(user_id, top_k)
    return {
        "message": "任务已接收，AI计算中...",
        "task_id": task.id,
        "code": 200
    }

# --- 修改点2: 增加缓存头控制 ---
@router.get("/recommend/status/{task_id}")
async def get_recommend_status(task_id: str):
    """获取推荐结果"""
    task_result = AsyncResult(task_id, app=celery_app)
    
    # 关键：告诉前端不要缓存这个状态查询接口
    # 如果是用 FastAPI，可以在 return 时加 headers，或者用装饰器
    if task_result.ready():
        if task_result.successful():
            result = task_result.result
            # 确保 result 是 dict 格式
            if isinstance(result, dict) and result.get("status") == "success":
                return {"status": "success", "data": result.get("data")}
            else:
                return {"status": "error", "message": result.get("error", "未知错误")}
        else:
            return {"status": "error", "message": "任务执行失败"}
    else:
        return {"status": "processing", "message": "AI正在计算中..."}
    