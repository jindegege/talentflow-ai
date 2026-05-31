# backend/app/rag/chain.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from fastapi.concurrency import run_in_threadpool
from app.core.config import settings

def get_rag_chain(vectorstore):
    # 1. 初始化 LLM
    llm = ChatOpenAI(
        api_key=settings.API_KEY,
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        temperature=0.7,
        streaming=True # 确保开启流式
    )

    # 2. 定义提示词
    template = """请根据以下参考信息回答用户的问题。
    如果参考信息中不包含答案，请根据你的通用知识回答。
    
    参考信息:
    {context}

    问题: {question}
    """
    prompt = ChatPromptTemplate.from_template(template)

    # 3. 定义同步检索逻辑 (耗时操作都在这里)
    def _sync_retrieve(query: str) -> str:
        try:
            # 强制刷新输出，确保能看到日志
            import sys
            print(f"[后台线程] 开始检索: {query}", flush=True)
            
            collection = vectorstore["collection"]
            embedding_func = vectorstore["embedding_function"]
            
            # A. 计算向量 (CPU密集)
            query_embedding = embedding_func.embed_query(query)
            
            # B. 查询数据库 (IO密集)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=3,
                include=['documents', 'metadatas', 'distances']
            )
            
            # C. 格式化结果
            if not results['documents'] or not results['documents'][0]:
                print("[后台线程] 未找到相关文档", flush=True)
                return "未找到相关参考资料。"
                
            docs = results['documents'][0]
            context = "\n---\n".join(docs)
            
            print(f"[后台线程] 检索完成，上下文长度: {len(context)}", flush=True)
            return context
            
        except Exception as e:
            print(f"[后台线程] 检索出错: {e}", flush=True)
            return "检索系统暂时不可用。"

    # 4. 定义异步包装器 (关键修复)

    async def _async_retrieve(input_data):
        # 1. 确保提取的是字符串
        query_text = ""
        if isinstance(input_data, str):
            query_text = input_data
        elif isinstance(input_data, dict) and "question" in input_data:
            query_text = input_data["question"]
        else:
            query_text = str(input_data) # 兜底

        # 2. 调用同步检索
        return await run_in_threadpool(_sync_retrieve, query_text)

    # 5. 构建链
    # 注意：这里必须传入异步函数 _async_retrieve
    rag_chain = (
        {
            "context": _async_retrieve, 
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain