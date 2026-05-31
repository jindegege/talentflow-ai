# app/agents/smart_apply/edges.py
from typing import Literal
from .state import AgentState

def route_after_fetch(state: AgentState) -> Literal["optimize_resume", "save_record"]:
    """
    路由函数：在获取简历（或查库）后，决定下一步去哪。
    
    逻辑：
    1. 如果 skip_generation 为 True，直接跳到 save_record (复用模式)。
    2. 如果为 False，走 optimize_resume (生成模式)。
    """
    if state.get("skip_generation", False) is True:
        print("路由决策：跳过生成，直接保存记录")
        return "save_record" # 直接跳过中间所有节点，去投递
    else:
        print("路由决策：进入优化流程")
        return "optimize_resume"