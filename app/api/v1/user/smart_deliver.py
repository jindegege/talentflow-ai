# app/api/smart_deliver.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Literal
from sqlalchemy.orm import Session
import logging

# --- 导入依赖 ---
# 1. 数据库相关
from app.models.database import get_db # 假设你的数据库会话依赖在这里
from app.models.user_resume_cache import UserResumeCache # 假设模型定义在 app/models.py

# 2. Agent 相关
from app.agents.graph import smart_apply_graph

from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env

router = APIRouter(prefix="/api/v1/user", tags=["智能投递"])
logger = logging.getLogger("api.smart_apply")



# ================= 1. 定义 Pydantic 模型 =================

class ApplyRequest(BaseModel):
    """
    前端请求体
    """
    user_id: int
    job_id: str
    job_description: str 
    resume_id: Optional[int] = None # 原始简历ID，可选
    mode: Literal["auto", "force_generate", "force_reuse"] = "auto"

class ApplyResponse(BaseModel):
    """
    返回给前端的响应体
    """
    success: bool
    message: str
    application_id: Optional[int] = None
    resume_id: Optional[int] = None
    cover_letter: Optional[str] = None
    is_reused: bool = False # 标记是否复用了旧简历
    error: Optional[str] = None

# ================= 2. 接口实现 =================

from langsmith import traceable

@router.post("/smart-apply", response_model=ApplyResponse)
@traceable(run_type="chain", name="smart_apply_api_call")
async def smart_apply_endpoint(
    data: ApplyRequest, 
    db: Session = Depends(get_db) # 注入数据库会话
):
    """
    智能投递核心接口
    逻辑：
    1. 查缓存表 -> 决定是复用还是生成
    2. 调用 Graph 执行
    3. 如果是新生成 -> 更新缓存表
    """
    logger.info(f"用户 {data.user_id} 发起投递请求 -> 职位 {data.job_id}, 模式: {data.mode}")

    try:
        # ==========================================
        # 第一步：查库决策 (Check Cache)
        # ==========================================
        existing_cache = None
        resume_id_to_use = None
        is_reused = False

        # 只有在非"强制生成"模式下才尝试查询复用
        if data.mode != "force_generate":
            existing_cache = db.query(UserResumeCache).filter(
                UserResumeCache.user_id == data.user_id,
                UserResumeCache.job_id == data.job_id
            ).first()

        if existing_cache and data.mode == "auto":
            # --- 场景 A: 命中缓存，复用模式 ---
            logger.info(f"命中缓存：发现针对 {data.job_id} 的优化简历 ID {existing_cache.optimized_resume_id}")
            
            resume_id_to_use = existing_cache.optimized_resume_id
            is_reused = True
            
            # 构造状态：标记跳过生成
            initial_state = {
                "user_id": data.user_id,
                "job_id": data.job_id,
                "job_description": data.job_description,
                "resume_id": resume_id_to_use,
                "skip_generation": True 
            }
            
        else:
            # --- 场景 B: 未命中或强制生成，走 AI 流程 ---
            logger.info("启动 AI 生成流程...")
            
            resume_id_to_use = data.resume_id # 使用原始简历 ID (如果前端传了)
            is_reused = False
            
            # 构造状态：正常生成
            initial_state = {
                "user_id": data.user_id,
                "job_id": data.job_id,
                "job_description": data.job_description,
                "resume_id": resume_id_to_use,
                "skip_generation": False 
            }

        # ==========================================
        # 第二步：调用 Graph 执行
        # ==========================================
        # 配置线程 ID，方便追踪
        config = {"configurable": {"thread_id": f"apply_{data.user_id}_{data.job_id}"}}
        
        # 异步调用 Graph
        result = await smart_apply_graph.ainvoke(initial_state, config)

        # ==========================================
        # 第三步：后处理与结果返回
        # ==========================================
        
        # 1. 检查 Graph 执行是否成功
        if result.get("error_message"):
            logger.error(f"Graph 执行失败: {result['error_message']}")
            return ApplyResponse(
                success=False,
                message="投递流程执行失败",
                error=result['error_message']
            )

        # 2. 提取结果数据
        final_resume_id = result.get("resume_id")
        final_app_id = result.get("application_id")
        final_cover_letter = result.get("cover_letter")

        # 3. 【关键】如果是新生成的简历，更新缓存表
        # 判断逻辑：原本是生成模式，且 Graph 返回了新的 resume_id
        if not is_reused and final_resume_id:
            logger.info(f"更新缓存：将新简历 {final_resume_id} 关联到职位 {data.job_id}")
            
            # 使用 merge 实现 "存在即更新，不存在即插入"
            cache_record = UserResumeCache(
                user_id=data.user_id,
                job_id=data.job_id,
                optimized_resume_id=final_resume_id
            )
            db.merge(cache_record)
            db.commit() # 提交事务

        # 4. 返回成功响应
        return ApplyResponse(
            success=True,
            message="简历复用成功" if is_reused else "AI 生成并投递成功",
            application_id=final_app_id,
            resume_id=final_resume_id,
            cover_letter=final_cover_letter,
            is_reused=is_reused
        )

    except Exception as e:
        # 全局异常捕获
        logger.error(f"系统内部错误: {str(e)}", exc_info=True)
        db.rollback() # 发生错误回滚数据库事务
        raise HTTPException(status_code=500, detail=f"系统内部错误: {str(e)}")