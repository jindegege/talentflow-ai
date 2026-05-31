from typing import List

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS # 导入 LangChain 的 FAISS 包装类
from langchain_core.runnables import RunnableParallel

from .reranker import global_reranker
from app.core.vector_store import get_vectorstore, get_all_documents
from app.utils.logger import logger


class HybridRetriever(BaseRetriever):
    """
    混合检索器：结合 BM25 (关键词) 和 FAISS (向量)
    """
    bm25_retriever: BM25Retriever
    vector_retriever: BaseRetriever
    k: int = 5
    bm25_weight: float = 0.3
    vector_weight: float = 0.7
    
    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        # 1. 并行执行两种检索
        retrieval_chain = RunnableParallel(
            bm25_results=self.bm25_retriever,
            vector_results=self.vector_retriever
        )
        results = retrieval_chain.invoke(query)
        
        # 2. 结果融合 (RRF 算法的简化版)
        scored_docs = {}
        
        # 处理 BM25 结果
        for i, doc in enumerate(results['bm25_results']):
            doc_id = doc.metadata.get('id') or doc.page_content[:20]
            if doc_id not in scored_docs:
                scored_docs[doc_id] = {"doc": doc, "score": 0.0}
            # 倒数排名融合
            scored_docs[doc_id]["score"] += self.bm25_weight * (1.0 / (i + 1))
        
        # 处理 Vector 结果
        for i, doc in enumerate(results['vector_results']):
            doc_id = doc.metadata.get('id') or doc.page_content[:20]
            if doc_id not in scored_docs:
                scored_docs[doc_id] = {"doc": doc, "score": 0.0}
            scored_docs[doc_id]["score"] += self.vector_weight * (1.0 / (i + 1))

        # 3. 排序并截取
        sorted_docs = sorted(scored_docs.values(), key=lambda x: x["score"], reverse=True)
        initial_docs = [item["doc"] for item in sorted_docs[:self.k*2]] # 先取多一些给 Rerank
        
        # 4. 重排序 (Rerank)
        if not initial_docs:
            return []
            
        final_docs = global_reranker.rank(query, initial_docs, top_k=self.k)
        return final_docs


class EmptyRetriever(BaseRetriever):
    """空检索器，防止数据库为空时报错"""
    def _get_relevant_documents(self, query: str) -> List[Document]:
        return []


def get_hybrid_retriever(k: int = 5):
    """
    构建混合检索器
    注意：这里不再接受 vectorstore_dict，而是直接在内部加载
    """
    # 1. 获取所有文档用于 BM25
    all_docs = get_all_documents()
    
    if not all_docs:
        logger.warning("警告：向量库为空，返回空检索器。")
        return EmptyRetriever()

    # 2. 初始化 BM25
    bm25_retriever = BM25Retriever.from_documents(all_docs)
    bm25_retriever.k = k * 5 

    # 3. 初始化 FAISS 向量检索器 (关键修复点)
    # 我们直接调用 get_vectorstore() 获取底层组件
    store = get_vectorstore()
    
    # 使用 LangChain 的 FAISS 类来包装现有的索引
    # 这样我们就可以直接使用 .as_retriever() 方法
    vectorstore = FAISS(
        embedding_function=store["embedding_function"],
        index=store["index"],
        docstore=None, # 我们主要靠 metadata 过滤，docstore 在这里不是必须的，除非你要通过 ID 查原文
        index_to_docstore_id={} 
    )
    
    # 手动把元数据挂载上去，或者在 search 时处理
    # 为了让 retriever 能工作，我们需要一个简单的 Docstore
    from langchain_core.stores import InMemoryByteStore
    from langchain_community.docstore.in_memory import InMemoryDocstore
    
    # 重建 Docstore 以便 FAISS 能返回完整的 Document 对象
    docstore = InMemoryDocstore()
    index_to_docstore_id = {}
    
    for i, meta in enumerate(store["metadatas"]):
        # 这里我们利用 metadata 重建 Document
        # 注意：FAISS 索引里只存了向量，原文必须从 metadatas 里找（如果存了的话）
        # 如果 metadatas 里没存 content，这里会比较麻烦。
        # 假设你的 sync 脚本把 content 存进了 metadatas['content']
        content = meta.get('content', meta.get('title', '')) 
        doc = Document(page_content=content, metadata=meta)
        doc_id = str(meta.get('id', i))
        docstore.add({doc_id: doc})
        index_to_docstore_id[i] = doc_id

    vectorstore.docstore = docstore
    vectorstore.index_to_docstore_id = index_to_docstore_id

    vector_retriever = vectorstore.as_retriever(search_kwargs={"k": k * 3})

    # 4. 返回混合检索器
    return HybridRetriever(
        bm25_retriever=bm25_retriever,
        vector_retriever=vector_retriever,
        k=k,
        bm25_weight=0.3,
        vector_weight=0.7
    )