# app/core/llm.py
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.utils.logger import logger

def get_llm():
    """初始化 LLM 模型"""
    llm = ChatOpenAI(
        api_key=settings.API_KEY,
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        temperature=0.7
    )
    logger.info(f"LLM 初始化成功！模型: {llm.model_name}")
    return llm