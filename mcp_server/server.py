# -*- coding: utf-8 -*-
"""
MCP Server 核心逻辑
功能：作为工具提供方，封装数据库操作（简历读取、投递记录写入、用户查询），
     并通过 MCP 协议暴露给 LangGraph Agent 使用。
"""

import asyncio
import logging
from fastmcp import FastMCP
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 导入本地定义的数据库模型
from app.models.application import Application
from app.models.resume import Resume
from app.models.user import User  # 导入 User 模型
from app.service.recommendation import get_recommendations_sync # 导入推荐逻辑

from typing import Union, Optional,Dict,Any # 引入 Optional

# =================================================================
# 1. 数据库配置
# =================================================================
DATABASE_URL = "mysql+aiomysql://root:123456@localhost:3306/dandelion_tribe"

# 创建异步数据库引擎
engine = create_async_engine(DATABASE_URL, echo=False)

# =================================================================
# 2. 初始化 MCP Server
# =================================================================
mcp = FastMCP("JobPlatform-Tools")

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("langgraph-agent")

# =================================================================
# 2. 新增：智能推荐工具
# =================================================================

@mcp.tool()
async def get_intelligent_job_recommendations(
    user_id: int,
    top_k: int = 5,
    min_score: float = 70.0
) -> Dict[str, Any]:
    """
    工具：获取智能职位推荐
    描述：调用 RAG + 混合检索算法，返回高匹配度的职位列表。
    """
    logger.info(f"[MCP] 正在为用户 {user_id} 获取智能推荐...")
    
    try:
        # --- 核心难点：在 Async 函数中调用 Sync Celery 逻辑 ---
        # 使用 run_in_executor 来避免阻塞事件循环
        # get_recommendations_sync 是我们封装好的同步接口
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, get_recommendations_sync, user_id, top_k)
        
        # --- 结果处理 ---
        if result.get("status") == "success":
            jobs = result.get("data", [])
            
            # 过滤低分职位
            filtered_jobs = [job for job in jobs if job.get("score", 0) >= min_score]
            
            logger.info(f"[MCP] 推荐成功，找到 {len(filtered_jobs)} 个符合条件的职位")
            return {
                "success": True,
                "data": filtered_jobs,
                "message": f"为您找到 {len(filtered_jobs)} 个高匹配度职位"
            }
        else:
            error_msg = result.get("error", "未知错误")
            logger.error(f"[MCP] 推荐失败: {error_msg}")
            return {
                "success": False,
                "data": [],
                "message": f"推荐失败: {error_msg}"
            }
            
    except Exception as e:
        logger.error(f"[MCP] 推荐工具异常: {e}")
        return {
            "success": False,
            "data": [],
            "message": f"系统异常: {str(e)}"
        }


# =================================================================
# 3. 定义 MCP 工具 (Tools)
# =================================================================
@mcp.tool()
async def get_resume_content(user_id: int) -> dict:
    """
    工具：获取简历内容
    描述：根据用户ID查询简历表，返回简历的纯文本内容
    """
    async with AsyncSession(engine) as session:
        stmt = select(Resume).where(Resume.user_id == user_id)
        result = await session.execute(stmt)
        resume = result.scalar_one_or_none()
        
        if not resume:
            return {"error": "未找到简历", "content": None}
            
        return {
        "id": resume.id,
        "name": resume.name,
        "content": resume.summary  # 将数据库的 summary 映射为 content
        }

@mcp.tool()
async def create_application_record(
    user_id: Union[int, str], 
    job_id: Union[int, str], 
    cover_letter: str,
    resume_id: Optional[int] = None # 允许为空，默认为None
) -> dict:
    """
    工具：创建投递记录
    描述：将生成的求职信、用户、职位和简历ID写入数据库
    """
    
    uid = int(user_id)
    job_id_str = str(job_id)
           
    async with AsyncSession(engine) as session:
        new_app = Application(
            user_id=uid,
            job_id=job_id_str,
            cover_letter=cover_letter,
            resume_id=resume_id, 
            status="applied" 
        )
        
        session.add(new_app)
        await session.commit()
        await session.refresh(new_app)
        
        return {"status": "success", "application_id": new_app.id}


# --- 工具函数 ---
@mcp.tool()
async def save_optimized_resume(user_id: int, content: str, job_id: str, name: str) -> Dict[str, Any]:
    """
    保存 AI 优化后的简历
    """
    async with AsyncSession(engine) as session:
        try:
            # 1. 创建新简历对象
            # 注意：这里假设你有一个 SQLAlchemy 模型类 Resume
            new_resume = Resume(
                user_id=user_id,
                name=name,
                content=content,           # 优化后的全文
                source="agent_optimized",  # 标记来源，便于前端区分
                target_job_id=job_id,      # 记录针对的职位
                # 其他必要字段的默认值
                status="Active",           # 默认激活
                is_default=False,          # 优化版通常不设为默认
                # ... 其他字段如 phone, email 可能需要从原简历复制，这里暂设空
                phone="",
                email=""
            )

            # 2. 添加并提交
            session.add(new_resume)
            await session.commit()
            await session.refresh(new_resume) # 刷新以获取数据库生成的 ID
            
            # 3. 返回成功信息
            return {
                "status": "success",
                "message": "简历保存成功",
                "data": {
                    "new_resume_id": new_resume.id,
                    "resume_title": new_resume.title
                }
            }

        except Exception as e:
            # 异步环境下使用 rollback
            await session.rollback()
            logging.error(f"保存优化简历失败 - 用户ID: {user_id}, 错误: {e}")
            return {
                "status": "error",
                "message": f"数据库操作异常: {str(e)}"
            }

# =================================================================
# 4. 运行 Server
# =================================================================
if __name__ == "__main__":
    mcp.run(transport='http', host='127.0.0.1', port=8002)