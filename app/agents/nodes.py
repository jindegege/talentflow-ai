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

# =================================================================
# 3. 全局 MCP 配置
# =================================================================
MCP_SERVER_URL = "http://127.0.0.1:8002/mcp"

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
# 定义工作流节点 (Nodes)
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

import json # <--- 1. 确保导入了 json 库
async def save_optimized_resume_node(state: AgentState) -> Dict[str, Any]:
    """节点 3: 保存优化后的简历"""
    logger.info(f"[Node] 正在保存优化后的简历...")
    if state.get("error_message"):
        return state

    try:
        async with Client(MCP_SERVER_URL) as client:
            # 构造参数
            tool_args = {
                "user_id": state['user_id'],
                "content": state['optimized_resume'],
                "job_id": state['job_id'],
                "name": f"{state['applicant_name']}_Optimized"
            }
            
            # 调用工具
            result = await client.call_tool("save_optimized_resume", tool_args)
            
            # --- 2. 修改这里：解析 CallToolResult 对象 ---
            
            # result 是 CallToolResult 对象，数据在 result.content 里
            # content 是一个列表，我们需要取出第一个元素
            if not result.content:
                return {"error_message": "MCP返回结果为空"}
            
            # 获取第一个内容块（通常是文本块）
            content_block = result.content[0]
            
            # 提取文本内容 (FastMCP 返回的通常是 TextContent 对象)
            if hasattr(content_block, 'text'):
                text_data = content_block.text
            else:
                # 兼容直接返回字符串的情况
                text_data = str(content_block)
            
            # 将 JSON 字符串解析为字典
            response_data = json.loads(text_data)
            
            # --- 3. 根据解析后的字典返回结果 ---
            if response_data.get("status") == "success":
                new_resume_id = response_data["data"]["new_resume_id"]
                return {
                    "resume_id": new_resume_id,
                    "final_resume_id": new_resume_id
                }
            else:
                return {"error_message": response_data.get("message", "未知错误")}
                
    except Exception as e:
        logger.error(f"保存优化简历异常: {e}")
        return {"error_message": f"保存异常: {str(e)}"}

async def save_optimized_resume_node(state: AgentState) -> Dict[str, Any]:
    """节点 3: 保存优化后的简历"""
    logger.info(f"[Node] 正在保存优化后的简历...")
    if state.get("error_message"):
        return state

    try:
        async with Client(MCP_SERVER_URL) as client:
            # --- 构造参数 ---
            tool_args = {
                "user_id": state['user_id'],
                "content": state['optimized_resume'],
                "job_id": state['job_id'], 
                "name": f"{state['applicant_name']}_Optimized"
            }
            
            # --- 调用工具 ---
            mcp_result = await client.call_tool("save_optimized_resume", tool_args)
            
            # --- 2. 核心修改：解析 CallToolResult 对象 ---
            
            # 第一步：从 mcp_result.content 列表中提取文本
            # FastMCP 返回的内容在 content 列表中，通常是第一个元素
            if not mcp_result.content:
                return {"error_message": "MCP返回结果为空"}
            
            content_block = mcp_result.content[0]
            
            # 提取 text 属性（这是 JSON 字符串）
            if hasattr(content_block, 'text'):
                json_str = content_block.text
            else:
                json_str = str(content_block)
            
            # 第二步：将 JSON 字符串转换为 Python 字典
            result_data = json.loads(json_str)
            
            # --- 3. 现在可以对字典使用 .get() 了 ---
            if result_data.get("status") == "success":
                new_resume_id = result_data["data"]["new_resume_id"]
                return {
                    "resume_id": new_resume_id,
                    "final_resume_id": new_resume_id
                }
            else:
                return {"error_message": result_data.get("message", "未知错误")}
                
    except Exception as e:
        logger.error(f"保存优化简历异常: {e}")
        return {"error_message": f"保存异常: {str(e)}"}

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
            # 1. 安全获取 cover_letter，如果没有则给个默认值
            # 使用 .get() 方法避免 KeyError
            cover_letter = state.get('cover_letter')
            
            if not cover_letter:
                # 如果是复用模式，可能没有生成求职信，这里给一个默认文本
                # 或者你可以选择去数据库查之前的求职信（如果需要）
                cover_letter = "您好，我对该职位非常感兴趣，这是我的最新简历，期待与您进一步沟通。"
                logger.warning("未找到求职信，使用默认文本代替")

            # --- 修改点结束 ---
            result = await client.call_tool(
                name="create_application_record",
                arguments={
                    "user_id": state['user_id'],
                    "job_id": str(state['job_id']),
                    "cover_letter": cover_letter,
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
