# 文件路径：app/services/rag_service.py
# 作用：RAG 核心业务逻辑（检索、Prompt组装、LLM调用）

from typing import List, Dict
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# 假设你的向量库实例已经在全局或单例中可用
from app.rag import vector_store 

# 假设你有配置好的 LLM 实例
# from app.core.llm import llm 

def retrieve_context(query: str, tenant_id: int, k: int = 3) -> List[Document]:
    """
    业务逻辑：从向量库检索上下文
    """
    # 使用向量库的检索功能，并强制过滤 tenant_id
    retriever = vector_store.collection.as_retriever(
        search_kwargs={
            "k": k,
            "where": {"tenant_id": tenant_id} # 核心：租户隔离
        }
    )
    docs = retriever.invoke(query)
    return docs

def generate_answer(query: str, context_docs: List[Document]) -> str:
    """
    业务逻辑：组装 Prompt 并调用大模型
    """
    # 1. 处理上下文文本
    context_text = "\n\n".join([doc.page_content for doc in context_docs])
    
    # 2. 定义 Prompt 模板
    template = """你是一个智能助手。请根据以下已知信息回答用户的问题。
    如果已知信息中不包含答案，请直接说“根据现有知识库无法回答”，不要编造事实。
    
    ---
    已知信息：
    {context}
    ---
    
    用户问题：{question}
    回答："""
    
    prompt = ChatPromptTemplate.from_template(template)
    
    # 3. 填充 Prompt
    final_prompt = prompt.format(context=context_text, question=query)
    
    # 4. 调用 LLM (这里需要替换为你实际的 LLM 调用代码)
    # response = llm.invoke(final_prompt)
    # return response.content
    
    # --- 模拟 LLM 返回 ---
    return f"[AI 思考中...] 基于检索到的 {len(context_docs)} 个片段，针对 '{query}' 的回答是：\n\n{context_text[:100]}..."

def run_rag_pipeline(user_message: str, tenant_id: int) -> str:
    """
    业务逻辑：RAG 完整流水线
    这是 chat.py 将会调用的主入口
    """
    # 1. 检索
    context = retrieve_context(user_message, tenant_id)
    
    # 2. 生成
    answer = generate_answer(user_message, context)
    
    return answer