# -*- coding: utf-8 -*-

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from app.core.config import settings

from app.utils.logger import logger


def get_rag_chain(vectorstore): 
    llm = get_llm()

    # 1. 定义提示词模板 (修改点：替换为增强版模板)
    # ==================================================================================
    # 替换这里的 template 字符串
    # ==================================================================================
    template = """
你是一个智能助手。请根据以下参考信息回答用户的问题。

### 规则：
1. 如果参考信息中包含答案，请依据参考信息回答，并保持客观。
2. 如果参考信息为空或与问题无关，请明确告知用户：“未在当前知识库找到相关信息”，然后基于你的通用知识提供建议。
3. 如果用户的问题涉及敏感、违规内容，请拒绝回答。
4. 回答要条理清晰，使用 Markdown 格式。

### 参考信息：
{context}

### 用户问题：
{question}

### 助手回答：
"""
    # ==================================================================================
    # 保持下面的 Prompt 初始化不变
    # ==================================================================================
    prompt = ChatPromptTemplate.from_template(template)

    # 2. 定义检索函数 (闭包) - 保持你现有的硬编码逻辑不变
    def retrieve_context(inputs):
        question = ""
        if isinstance(inputs, dict):
            question = inputs.get("input", "")
        elif isinstance(inputs, str):
            question = inputs
        else:
            question = str(inputs)

        logger.info(f"正在检索问题: {question[:50]}...")
        try:
            # ==========================================
            # 核心修复：直接使用传入的 vectorstore 进行检索
            # ==========================================

            # 1. 获取集合对象
            collection = vectorstore["collection"]

            # 2. 将问题向量化
            embedding_func = vectorstore["embedding_function"]
            logger.info(f"[RAG] 正在计算向量...")
            query_vector = embedding_func.embed_documents([question])

            # 3. 原生 ChromaDB 查询方式
            logger.info("[RAG] 正在查询 ChromaDB...")
            query_results = collection.query(
                query_embeddings=query_vector,
                n_results=3
            )

            # 4. 提取文档内容
            docs_content = query_results['documents'][0]

            # 5. 拼接
            context = "\n\n".join(docs_content)
            return context

        except Exception as e:
            logger.error(f"检索出错了！错误信息: {e}")
            return ""

    # 3. 构建链 (保持不变)
    rag_chain = (
        {
            "context": retrieve_context, # 使用上面自定义的检索函数
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain


def get_llm():
    """
    初始化 LLM 模型
    """
    llm = ChatOpenAI(
        api_key=settings.API_KEY,
        base_url="https://api.deepseek.com",
        model="deepseek-chat",
        temperature=0.7
    )

    logger.info(f"LLM 初始化成功！模型: {llm.model_name}")
    return llm