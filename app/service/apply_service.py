# -*- coding: utf-8 -*-
"""
智能投递服务入口
包含：数据库复用逻辑 + MCP 获取原始简历逻辑
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from typing import Dict, Any
from app.models.resume import Resume
import logging

logger = logging.getLogger(__name__)

# 1. 检查是否已有现成的优化简历
async def run_smart_apply(
    db: AsyncSession, # 数据库会话
    user_id: int,
    job_id: str,
    job_desc: str
) -> Dict[str, Any]:
    """
    智能投递主逻辑：
    1. 检查是否已有针对该职位的优化简历。
    2. 如果有，直接复用（跳过生成）。
    3. 如果没有，启动 Agent 生成并投递。
    """
    
    # --- 第一步：查询数据库是否存在 "agent_optimized" 且 "target_job_id" 匹配的简历 ---
    # 请根据你的实际 Resume 模型字段调整这里的查询条件
    stmt = select(Resume).where(
        Resume.user_id == user_id,
        Resume.target_job_id == job_id,
        Resume.source == "agent_optimized", # 确保只复用 AI 生成的简历
        Resume.is_deleted == False
    )
    result = await db.execute(stmt)
    existing_resume = result.scalars().first()

    if existing_resume:
        # --- 场景 A：已有现成简历，直接复用 ---
        logger.info(f"用户 {user_id} 针对职位 {job_id} 已有优化简历 (ID: {existing_resume.id})，跳过生成。")
        
        # 构造状态
        # 注意：这里不再需要调用 MCP 获取原始简历，因为我们直接复用优化后的结果
        state = {
            "user_id": user_id,
            "job_id": job_id,
            "job_desc": job_desc,
            
            # --- 关键：伪造 Resume 相关字段 ---
            # 这里的字段名必须和你的 State 定义完全一致
            "resume_content": existing_resume.content, # 原始简历内容（如果投递节点需要）
            "optimized_resume": existing_resume.content, # 优化后内容（复用）
            "applicant_name": existing_resume.applicant_name or "求职者",
            "resume_id": existing_resume.id, # 关键 ID
            
            # --- 控制流标记 ---
            # 如果你的 Graph 逻辑中有条件边（Conditional Edges），
            # 建议在这里加一个标记，告诉 Graph 跳过 "生成节点" 和 "保存节点"
            "skip_generation": True, 
            "is_reused": True
        }
        
        # 注意：这里我们直接返回状态给调用方（FastAPI 路由）
        # 由路由层决定是直接调用 submit_application_node 还是 invoke 整个 Graph
        # 如果你的 Graph 支持 "skip_generation" 标记，可以直接调用 graph.ainvoke(state)
        
        return {
            "status": "success",
            "message": "检测到已有优化简历，已准备复用",
            "data": state,
            "is_reused": True
        }

    else:
        # --- 场景 B：没有现成简历，启动完整 Agent 流程 ---
        logger.info(f"用户 {user_id} 针对职位 {job_id} 无现成简历，准备启动 Agent...")
        
        # 构造初始输入状态
        # 注意：这里我们只传基础信息，不传简历内容
        # Resume 内容将由 Graph 的第一个节点 (fetch_resume_node) 通过 MCP 去获取
        initial_state = {
            "user_id": user_id,
            "job_id": job_id,
            "job_desc": job_desc,
            
            # --- 留空给 MCP 填充 ---
            # fetch_resume_node 节点会负责调用 MCP 并填充这些字段
            "resume_content": None, 
            "applicant_name": None,
            "resume_id": None, # 这里是原始简历 ID
            
            # --- 控制流标记 ---
            "skip_generation": False, 
            "is_reused": False,
            
            # --- 错误处理 ---
            "error_message": None
        }
        
        # 注意：这里不直接运行 Graph，而是返回状态
        # 让外部的 Controller 决定如何运行 Graph
        # 这样可以保持 Service 层的纯粹性
        
        return {
            "status": "success",
            "message": "准备启动 Agent 生成新简历",
            "data": initial_state,
            "is_reused": False
        }