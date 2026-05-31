from typing import List, Tuple
from langchain_core.documents import Document
from cachetools import LRUCache

class RerankerService:
    def __init__(self, max_cache_size: int = 1000):
        # 1. 这里不再加载模型，直接初始化缓存
        self.cache = LRUCache(maxsize=max_cache_size)
        print("重排序服务（Reranker Service）初始化完成")

    def rank(self, query: str, documents: List[Document], top_k: int = 3, max_rerank_limit: int = 20):
        """
        对文档列表进行重排序
        """
        # 2. 从全局 model_loader 导入已经加载好的模型实例
        from app.core.model_loader import get_reranker_model    
        model = get_reranker_model()
        if not model:
            # 如果模型没加载成功，直接返回截断的原文档，防止报错
            print("严重警告：重排序模型未加载！请检查 model_loader.py 的加载日志。")
            return documents[:top_k]

        if not documents:
            return []

        # 3. 限制最大重排数量，防止 CPU/GPU 爆炸
        docs_to_rerank = documents[:max_rerank_limit]

        # 4. 缓存机制
        cache_key = (query, tuple(doc.page_content for doc in docs_to_rerank))
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 5. 准备数据对并计算分数
        pairs = [[query, doc.page_content] for doc in docs_to_rerank]
        # 调用全局单例模型进行推理
        scores = model.compute_score(pairs, normalize=True) 

        # 确保分数是列表格式
        if isinstance(scores, float): 
            scores = [scores]
        
        # 6. 绑定并排序
        doc_score_pairs: List[Tuple[Document, float]] = list(zip(docs_to_rerank, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # 7. 截取 Top K
        top_docs = [doc for doc, score in doc_score_pairs[:top_k]]
        
        # 存入缓存
        self.cache[cache_key] = top_docs
        
        return top_docs

# 全局单例（只包含业务逻辑和缓存，不包含模型权重）
global_reranker = RerankerService()