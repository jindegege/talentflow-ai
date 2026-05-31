# app/rag/retriever.py
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

# 假设你的 vector_store.py 在同级目录
from .vector_store import get_all_documents

from app.utils.logger import logger

class HybridRetriever(BaseRetriever):
    """
    一个自定义的混合检索器，结合了 BM25 和向量检索。
    它独立于 langchain_experimental，更加稳定可靠。
    """
    bm25_retriever: BM25Retriever
    vector_retriever: BaseRetriever
    k: int = 5
    # 权重：bm25_weight + vector_weight = 1.0
    bm25_weight: float = 0.3
    vector_weight: float = 0.7

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        # 1. 并行执行两种检索
        # 使用 RunnableParallel 同时调用两个检索器
        retrieval_chain = RunnableParallel(
            bm25_results=self.bm25_retriever,
            vector_results=self.vector_retriever
        )
        
        # 执行检索
        results = retrieval_chain.invoke(query)
        bm25_docs = results['bm25_results']
        vector_docs = results['vector_results']

        # 2. 简单的结果融合
        # 这里使用一种简单的加权得分融合方法
        # 为每个文档计算一个综合得分
        scored_docs = {}

        # 处理 BM25 结果 (排名越靠前，得分越高)
        for i, doc in enumerate(bm25_docs):
            doc_id = id(doc) # 使用文档对象的id作为唯一标识
            if doc_id not in scored_docs:
                scored_docs[doc_id] = {"doc": doc, "score": 0.0}
            # 使用倒数排名作为分数
            scored_docs[doc_id]["score"] += self.bm25_weight * (1.0 / (i + 1))

        # 处理向量检索结果
        for i, doc in enumerate(vector_docs):
            doc_id = id(doc)
            if doc_id not in scored_docs:
                scored_docs[doc_id] = {"doc": doc, "score": 0.0}
            # 使用倒数排名作为分数
            scored_docs[doc_id]["score"] += self.vector_weight * (1.0 / (i + 1))

        # 3. 根据综合得分排序并返回 top-k
        sorted_docs = sorted(scored_docs.values(), key=lambda x: x["score"], reverse=True)
        final_docs = [item["doc"] for item in sorted_docs[:self.k]]
        
        return final_docs

class EmptyRetriever(BaseRetriever):
    """一个永远返回空结果的检索器，用于防止空库报错"""
    def _get_relevant_documents(self, query: str) -> List[Document]:
        return []

def get_hybrid_retriever(current_tenant_id,vectorstore_dict, k: int = 5):
    """
    获取混合检索器实例。
    """
    # 1. 获取所有文档用于构建 BM25 索引
    all_docs = get_all_documents(current_tenant_id)
    
    if not all_docs:
        logger.warning(f"警告：租户 {current_tenant_id} 的向量库为空，返回空检索器。")
        return EmptyRetriever() # <--- 修改这里：返回空检索器而不是 None

    # 2. 创建 BM25 检索器
    # 注意：这里我们直接使用 BM25Retriever，它不依赖易变的实验包
    bm25_retriever = BM25Retriever.from_documents(all_docs)
    # 设置 BM25 检索时返回的文档数量，可以设置得大一些，以便融合
    bm25_retriever.k = k * 5 

    # 3. 创建向量检索器
    # 使用你原有的 vectorstore 来创建
    collection = vectorstore_dict["collection"]
    embedding_func = vectorstore_dict["embedding_function"]
    
    # 这里我们创建一个简单的向量检索器
    # 由于你用的是原生 chromadb，我们需要一个简单的包装
    from langchain_chroma import Chroma
    # 使用一个临时的 Chroma 实例来作为 retriever
    # 这样可以复用你已经写好的 embedding_function
    temp_vectorstore = Chroma(
        client=vectorstore_dict["client"],
        collection_name=collection.name,
        embedding_function=embedding_func
    )
    vector_retriever = temp_vectorstore.as_retriever(search_kwargs={"k": k * 3})

    # 4. 返回我们自定义的混合检索器
    return HybridRetriever(
        bm25_retriever=bm25_retriever,
        vector_retriever=vector_retriever,
        k=k,
        bm25_weight=0.3, # 可以根据需要调整权重
        vector_weight=0.7
    )