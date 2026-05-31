# app/api/routes.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import logging

# --- 核心修改：导入 Agent 的执行函数 ---
# 确保路径正确：从 agents 包中导入 smart_apply_agent 模块的 run_smart_apply 函数
from app.agents.smart_apply_agent import run_smart_apply 

router = APIRouter(prefix="/api/v1/user", tags=["智能投递"])

# ================= 1. 定义 Pydantic 模型 =================

class ApplyRequest(BaseModel):
    """
    前端请求体
    修改点：新增 resume_id，由前端指定使用哪份简历
    """
    user_id: int
    job_id: str
    job_description: str 
    resume_id: int | None = None # 允许为空，用于智能生成

class ApplyResponse(BaseModel):
    """
    返回给前端的响应体
    """
    success: bool
    message: str
    application_id: Optional[int] = None
    resume_id: Optional[int] = None  # 返回使用的简历ID
    cover_letter: Optional[str] = None
    error: Optional[str] = None

# ================= 2. 定义接口 =================

@router.post("/smart-apply", response_model=ApplyResponse)
async def smart_apply_endpoint(data: ApplyRequest):
    """
    智能投递接口
    流程：调用 Agent -> 等待执行结果 -> 返回给前端
    """
    logger = logging.getLogger("api.smart_apply")

    logger.info(f"收到投递请求: 用户 {data.user_id} -> 职位 {data.job_id}")

    try:
        # 调用 Agent 执行函数
        # 注意：这里将 data.resume_id 传入，Agent 内部判断是生成还是复用
        result = await run_smart_apply(
            user_id=data.user_id, 
            job_id=data.job_id, 
            job_desc=data.job_description,
            resume_id=data.resume_id 
        )

        # --- 处理 Agent 返回结果 ---
        if result.get("success"):
            final_state = result["data"]
            
            return ApplyResponse(
                success=True,
                message="投递成功",
                # 从 Agent 的最终状态中提取字段
                application_id=final_state.get("application_id"),
                resume_id=final_state.get("resume_id"), # 返回简历ID
                cover_letter=final_state.get("cover_letter")
            )
        else:
            # --- 处理 Agent 内部错误 ---
            logger.error(f"Agent 执行失败: {result.get('error')}")
            return ApplyResponse(
                success=False,
                message="投递流程执行失败",
                error=result.get("error", "未知错误")
            )

    except Exception as e:
        # --- 处理系统级异常 ---
        logger.error(f"API 处理异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"系统内部错误: {str(e)}")