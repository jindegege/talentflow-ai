# 用于查询本地职位库

from sqlalchemy.orm import Session
from app.models import base

def search_local_jobs_tool(query: str, db: Session):
    """
    [MCP 工具] 搜索本地职位库
    这是 AI 可以调用的外部工具，模拟 MCP 服务
    """
    # 1. 执行数据库查询
    jobs = db.query(base.JobDB)\
             .filter(base.JobDB.title.contains(query))\
             .limit(3)\
             .all()
    
    # 2. 格式化结果为字符串，供 LLM 理解
    if not jobs:
        return "未找到相关职位。"
        
    result_str = "找到以下职位：\n"
    for job in jobs:
        result_str += f"- {job.title} ({job.company}): {job.location}\n"
        
    return result_str