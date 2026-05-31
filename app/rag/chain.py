# -*- coding: utf-8 -*-

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import numpy as np # 引入 numpy
import faiss      # 引入 faiss

from app.utils.logger import logger
from app.core.vector_store import get_vectorstore
from app.core.llm import get_llm

def get_rag_chain(): 
    llm = get_llm()

    # 1. 定义提示词模板
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
    prompt = ChatPromptTemplate.from_template(template)

    # 2. 定义检索函数 (核心修复逻辑在这里)
    def retrieve_context(inputs):
        # 解析输入
        question = ""
        if isinstance(inputs, dict):
            question = inputs.get("input", "")
        elif isinstance(inputs, str):
            question = inputs
        else:
            question = str(inputs)

        if not question.strip():
            return "用户未输入有效问题。"

        logger.info(f"正在检索问题: {question[:50]}...")
        
        try:
            # --- 获取向量库实例 ---
            vectorstore = get_vectorstore()
            index = vectorstore["index"]
            metadatas = vectorstore["metadatas"]
            embedding_func = vectorstore["embedding_function"]

            # --- 修复点 1：检查索引是否为空 ---
            if index.ntotal == 0:
                logger.warning("FAISS 索引为空，跳过检索")
                return ""

            # --- 获取查询向量 ---
            query_vector = embedding_func.embed_query(question)
            query_vector = np.array([query_vector]).astype('float32')
            
            # --- 修复点 2：确保查询向量已归一化 ---
            # 如果向量模长为0，normalize_L2 会处理它，或者我们可以手动检查
            norm = np.linalg.norm(query_vector)
            if norm < 1e-9:
                logger.error("查询向量为零向量，跳过检索")
                return ""
                
            faiss.normalize_L2(query_vector)

            # --- 执行检索 ---
            k = 3 # 取前3个
            # 如果库里的数据少于 k，search 会返回实际数量
            if index.ntotal < k:
                k = index.ntotal

            distances, indices = index.search(query_vector, k)
            
            # --- 提取结果 ---
            contexts = []
            # indices 是一个二维数组 [[0, 1, 2]]，我们需要遍历它
            for idx in indices[0]:
                if idx != -1 and 0 <= idx < len(metadatas):
                    # 这里假设 metadatas 是列表，且索引对应
                    # 你可以根据需要提取 title, company 等字段拼接到 context 中
                    meta = metadatas[idx]
                    content = f"职位: {meta.get('title')}, 公司: {meta.get('company')}, 要求: {meta.get('skills')}"
                    contexts.append(content)
            
            return "\n\n".join(contexts)

        except Exception as e:
            logger.error(f"检索过程中发生错误: {e}")
            # 发生错误时返回空字符串，让 LLM 自由发挥或提示无信息
            return ""

    # 3. 构建链
    rag_chain = (
        {
            "context": retrieve_context, 
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return rag_chain
