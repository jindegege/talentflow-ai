# -*- coding: utf-8 -*-
"""
智能投递 Agent 核心逻辑
功能：基于用户ID和职位描述，自动完成简历获取 -> 简历优化 -> 求职信生成 -> 记录保存的全流程
"""

import os
import json
import logging
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.redis import RedisSaver
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from fastmcp import Client

from app.core.config import settings

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("langgraph-agent")

# =================================================================
# 1. 定义状态 (State)
# =================================================================
class AgentState(TypedDict):
    user_id: int
    job_id: str
    job_description: str
    
    # 简历相关
    resume_content: Annotated[str, lambda x, y: y or x]  # 保留非空值
    optimized_resume: Annotated[Optional[str], lambda x, y: y or x]
    applicant_name: Annotated[Optional[str], lambda x, y: y or x]
    resume_id: Annotated[Optional[int], lambda x, y: y or x] # 关键：用于传递简历ID
    
    # 信件与结果
    cover_letter: Annotated[Optional[str], lambda x, y: y or x]
    application_id: Annotated[Optional[int], lambda x, y: y or x]
    
    error_message: Annotated[Optional[str], lambda x, y: y or x]

# =================================================================
# 2. 初始化核心组件 (LLM)
# =================================================================
# 注意：这里假设你有一个环境变量或配置文件
# 如果没有，请替换为具体的 API Key
llm = ChatOpenAI(
    api_key=settings.API_KEY, 
    base_url="https://api.deepseek.com/v1", # DeepSeek 官方地址通常带 /v1
    model="deepseek-chat",
    temperature=0.7
)

# =================================================================
# 3. 全局 MCP 配置
# =================================================================
MCP_SERVER_URL = "http://127.0.0.1:8002/mcp"

async def get_mcp_tools():
    """动态建立与 MCP Server 的连接并获取工具列表"""
    try:
        async with Client(MCP_SERVER_URL) as client:
            tools_list = await client.list_tools()
            tools_dict = {tool.name: tool for tool in tools_list}
            logger.info(f"成功从 MCP Server 获取工具: {list(tools_dict.keys())}")
            return tools_dict
    except Exception as e:
        logger.error(f"连接 MCP Server 失败: {e}")
        return {}

# =================================================================
# 4. 定义工作流节点 (Nodes)
# =================================================================

async def fetch_resume_node(state: AgentState, config: RunnableConfig):
    """节点 1: 获取简历"""
    logger.info(f"[MCP Node] 正在通过 MCP 获取用户 {state['user_id']} 的简历...")
    try:
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(
                "get_resume_content",
                {"user_id": state['user_id']}
            )
            
        if not result or not result.content:
            return {"error_message": "获取简历返回为空"}

        # 解析内容
        content_item = result.content[0]
        if isinstance(content_item, str):
            content_text = content_item
        elif hasattr(content_item, 'text'):
            content_text = content_item.text
        elif isinstance(content_item, dict) and 'value' in content_item:
            content_text = content_item['value']
        else:
            content_text = str(content_item)

        data = json.loads(content_text)
        if data.get("error"):
            return {"error_message": data["error"]}

        return {
            "resume_content": data["content"],
            "applicant_name": data.get("name", "求职者"),
            "resume_id": data.get("id")
        }
        
    except Exception as e:
        logger.error(f"调用 fetch_resume_node 失败: {e}")
        return {"error_message": f"MCP 调用失败: {str(e)}"}


async def optimize_resume_node(state: AgentState):
    """节点 2: 优化简历"""
    logger.info("[Node] 正在使用 AI 优化简历...")
    
    if state.get("error_message"):
        return state

    # 1. 定义优化 Prompt
    OPTIMIZE_PROMPT = ChatPromptTemplate.from_messages([
        ("system", """
        你是一位资深 HR 专家。请根据目标职位描述，优化用户的简历内容。
        要求：
        1. 保持原始简历的结构（如个人信息、教育、经历）。
        2. 重点润色「工作经历」和「项目经验」，使用 STAR 法则（情境、任务、行动、结果）。
        3. 自然植入职位描述中的关键词。
        4. 量化成果，突出数据。
        5. 不要编造用户没有的经历。
        6. 输出格式为 Markdown。
        """),
        ("human", "目标职位：\n{job_desc}\n\n原始简历：\n{resume}")
    ])

    chain = OPTIMIZE_PROMPT | llm

    try:
        response = await chain.ainvoke({
            "job_desc": state['job_description'],
            "resume": state['resume_content']
        })
        
        return {
            "optimized_resume": response.content,
            "applicant_name": state.get('applicant_name')
        }
    except Exception as e:
        logger.error(f"简历优化失败: {e}")
        return {"error_message": f"简历优化失败: {str(e)}"}


async def save_optimized_resume_node(state: AgentState):
    """节点 3: 保存优化后的简历"""
    logger.info(f"[Node] 正在保存优化后的简历到数据库 (Job: {state.get('job_id')})...")
    
    if state.get("error_message"):
        logger.warning("检测到前置节点有错误，跳过保存。")
        return state
        
    try:
        async with Client(MCP_SERVER_URL) as client:
            # --- 修改开始：构建完整的参数 ---
            tool_args = {
                "user_id": state['user_id'],
                "content": state['optimized_resume'],
                "job_id": state['job_id'],
                "name": state['applicant_name'],
                # 新增字段：标记来源为 AI 生成
                "source": "agent_optimized", 
                # 新增字段：明确关联的目标职位 ID
                "target_job_id": state['job_id'] 
            }
            # --- 修改结束 ---

            result = await client.call_tool(
                "save_optimized_resume",
                tool_args
            )

        if result.content:
            content_item = result.content[0]
            # 兼容处理：无论是 text 属性还是直接转字符串
            text_content = getattr(content_item, 'text', str(content_item))
            response_data = json.loads(text_content)
                
            if response_data.get("status") == "success":
                new_id = response_data["data"]["new_resume_id"]
                logger.info(f"优化简历保存成功，新ID: {new_id}")
                # 关键：更新 resume_id，供后续节点（如写求职信或投递）使用
                return {"resume_id": new_id}
            else:
                error_msg = response_data.get("message", "保存失败")
                logger.error(f"保存失败: {error_msg}")
                return {"error_message": error_msg}
                
    except Exception as e:
        logger.error(f"保存优化简历异常: {e}", exc_info=True)
        return {"error_message": f"保存工具调用异常: {str(e)}"}

async def generate_letter_node(state: AgentState):
    """节点 4: 生成求职信"""
    logger.info("[Node] 正在生成求职信...")
    
    if state.get("error_message"):
        return state

    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一名求职专家。根据简历和职位描述写一封简短有力的求职信。"
                   "落款处使用姓名: {applicant_name}。"),
        ("human", "简历:\n{resume}\n\n职位:\n{job_desc}\n\n求职信:")
    ])
    
    chain = prompt | llm
    
    try:
        # 决定使用哪个简历内容：优先使用优化后的，如果没有则用原始的
        final_resume = state.get('optimized_resume') or state['resume_content']
        
        response = await chain.ainvoke({
            "resume": final_resume,
            "job_desc": state['job_description'],
            "applicant_name": state.get('applicant_name', '求职者')
        })
        
        return {"cover_letter": response.content}
        
    except Exception as e:
        return {"error_message": f"生成求职信失败: {str(e)}"}


async def save_record_node(state: AgentState):
    """节点 5: 保存投递记录"""
    logger.info("[Node] 正在保存投递记录...")
    
    if state.get("error_message"):
        return state

    try:
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(
                name="create_application_record",
                arguments={
                    "user_id": state['user_id'],
                    "job_id": str(state['job_id']),
                    "cover_letter": state['cover_letter'],
                    "resume_id": state['resume_id'] # 这里使用的是最新的 resume_id
                }
            )

        # 解析结果
        if result.content:
            content_item = result.content[0]
            text_data = content_item.text if hasattr(content_item, 'text') else str(content_item)
            response_data = json.loads(text_data)
            
            return {"application_id": response_data.get("id", 0)}
            
    except Exception as e:
        logger.error(f"保存记录失败: {e}")
        return {"error_message": f"保存记录异常: {str(e)}"}

# =================================================================
# 5. 构建图 (Graph)
# =================================================================
def build_graph():
    """构建有向无环图 (DAG)"""
    builder = StateGraph(AgentState)
    
    # 添加节点
    builder.add_node("fetch_resume", fetch_resume_node)
    builder.add_node("optimize_resume", optimize_resume_node)
    builder.add_node("save_optimized_resume", save_optimized_resume_node)
    builder.add_node("generate_letter", generate_letter_node)
    builder.add_node("save_record", save_record_node)
    
    # 定义边
    builder.add_edge(START, "fetch_resume")
    builder.add_edge("fetch_resume", "optimize_resume")
    builder.add_edge("optimize_resume", "save_optimized_resume")
    builder.add_edge("save_optimized_resume", "generate_letter")
    builder.add_edge("generate_letter", "save_record")
    builder.add_edge("save_record", END)
    
    return builder.compile()

# 实例化图
smart_apply_graph = build_graph()

# =================================================================
# 6. 持久化层 (Redis Checkpointer)
# =================================================================
try:
    # 注意：RedisSaver 需要安装 redis 包
    redis_saver = RedisSaver.from_conn_string("redis://localhost:6379/0")
    # 在 LangGraph 0.1+ 中，需要先 setup
    redis_saver.setup()
    smart_apply_graph.checkpointer = redis_saver
    logger.info("Redis 检查点已连接")
except Exception as e:
    logger.warning(f"Redis 连接失败: {e}，将使用内存模式运行")

# =================================================================
# 7. 服务入口 (Service Layer)
# =================================================================
async def run_smart_apply(user_id: int, job_id: str, job_desc: str,resume_id: int):
    """
    对外暴露的调用接口
    注意：这里不再需要传入 resume_id，因为我们是新建简历。
    如果需要复用旧逻辑，保留 resume_id 参数并加入 state 即可。
    """
    inputs = {
        "user_id": user_id,
        "job_id": job_id,
        "job_description": job_desc,
        # 初始化空字段
        "resume_content": "",
        "optimized_resume": "",
        "cover_letter": "",
        "applicant_name": "",
        "resume_id": resume_id,
        "application_id": 0,
        "error_message": ""
    }
    
    config = {
        "configurable": {
            "thread_id": f"apply_{user_id}_{job_id}_{int(datetime.now().timestamp())}"
        }
    }
    
    try:
        # stream_mode="values" 是标准模式
        async for event in smart_apply_graph.astream(inputs, config, stream_mode="values"):
            # 这里可以打印每一步的状态用于调试
            # print(event)
            pass
        
        # 返回最终状态
        return {"success": True, "data": event}
        
    except Exception as e:
        return {"success": False, "error": str(e)}