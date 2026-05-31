# app/agents/smart_apply/graph.py
from langgraph.graph import StateGraph, START,END
from .nodes import (
    fetch_resume_node,
    optimize_resume_node,
    save_optimized_resume_node,
    generate_letter_node,
    save_record_node
)
from .edges import route_after_fetch
from .state import AgentState
from langgraph.checkpoint.redis import RedisSaver
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def build_graph():
    builder = StateGraph(AgentState)

    # --- 添加所有节点 ---
    builder.add_node("fetch_resume", fetch_resume_node)
    builder.add_node("optimize_resume", optimize_resume_node)
    builder.add_node("save_optimized_resume", save_optimized_resume_node)
    builder.add_node("generate_letter", generate_letter_node)
    builder.add_node("save_record", save_record_node)

    # --- 定义边 (Edges) ---
    # 1. 开始 -> 获取简历
    builder.add_edge(START, "fetch_resume")
    
    # 2. 获取简历 -> [条件边] -> 决定是跳过还是生成
    builder.add_conditional_edges(
        "fetch_resume",      # 源节点
        route_after_fetch,   # 路由函数
        { 
            "optimize_resume": "optimize_resume", # 如果走生成
            "save_record": "save_record"          # 如果走复用
        }
    )

    # 3. 如果走生成流程，连接后续节点
    builder.add_edge("optimize_resume", "save_optimized_resume")
    builder.add_edge("save_optimized_resume", "generate_letter")
    builder.add_edge("generate_letter", "save_record")
    
    # 4. 结束
    builder.add_edge("save_record", END)

    return builder.compile()

# --- 初始化 Graph 实例 ---
smart_apply_graph = build_graph()

# --- 配置持久化 (Redis) ---
try:
    redis_saver = RedisSaver.from_conn_string(settings.REDIS_URL)
    redis_saver.setup()
    smart_apply_graph.checkpointer = redis_saver
    logger.info("Redis 检查点已连接")
except Exception as e:
    logger.warning(f"Redis 连接失败: {e}，将使用内存模式运行")