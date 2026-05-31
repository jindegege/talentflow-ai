# app/agents/smart_apply/state.py
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph

class AgentState(TypedDict):
    user_id: int
    job_id: str
    job_description: str
    
    # 简历相关
    resume_content: Annotated[str, lambda x, y: y or x]
    optimized_resume: Annotated[Optional[str], lambda x, y: y or x]
    applicant_name: Annotated[Optional[str], lambda x, y: y or x]
    resume_id: Annotated[Optional[int], lambda x, y: y or x]
    
    # 信件与结果
    cover_letter: Annotated[Optional[str], lambda x, y: y or x]
    application_id: Annotated[Optional[int], lambda x, y: y or x]
    error_message: Annotated[Optional[str], lambda x, y: y or x]
    
    # --- 新增：控制流标记 ---
    # 用于控制边（Edges）的跳转逻辑
    skip_generation: Annotated[bool, lambda x, y: y or x]