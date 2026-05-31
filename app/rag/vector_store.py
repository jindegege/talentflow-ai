import os
import chromadb
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document

from app.core.config import settings
from app.rag.embedding import get_embedding_function
from app.utils.logger import logger

# 缓存客户端实例，避免重复初始化
_client_cache: Dict[str, Any] = {}

def get_vectorstore(tenant_id: Optional[int] = None):
    """
    获取或创建向量数据库实例。
    
    参数:
        tenant_id: 租户ID。如果提供，将基于该ID创建隔离的Collection。
                   如果为None，则使用全局默认Collection（主要用于后台管理或迁移脚本）。
    """
    embedding_func = get_embedding_function()
    
    # 1. 确保目录存在
    db_path = settings.VECTOR_DB_PATH
    if not os.path.exists(db_path):
        os.makedirs(db_path)

    # 2. 获取客户端（单例模式优化）
    # Chroma PersistentClient 线程安全，可以复用
    if "client" not in _client_cache:
        _client_cache["client"] = chromadb.PersistentClient(path=db_path)
    client = _client_cache["client"]

    # 3. 动态生成集合名称
    # 核心改动：如果传入了 tenant_id，则使用专属集合名
    if tenant_id:
        collection_name = f"{settings.CHROMA_COLLECTION_NAME}_tenant_{tenant_id}"
    else:
        collection_name = f"{settings.CHROMA_COLLECTION_NAME}_global"
        
    logger.info(f"正在连接向量库集合: {collection_name}")

    # 4. 获取或创建集合
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"} # 使用余弦相似度
    )

    return {
        "client": client,
        "collection": collection,
        "embedding_function": embedding_func
    }

def add_documents_to_vectorstore(documents: List, tenant_id: int):
    """
    将文档块存入向量数据库（特定租户）。
    """
    # 传入 tenant_id 获取隔离的 store
    store = get_vectorstore(tenant_id=tenant_id)
    collection = store["collection"]
    embedding_func = store["embedding_function"]
    
    texts = []
    metadatas = []
    
    for i, doc in enumerate(documents):
        if isinstance(doc, dict):
            texts.append(doc.get('content', '')) 
            meta = doc.get('metadata', {})
            metadatas.append(meta)
        else:
            texts.append(doc.page_content)
            meta = doc.metadata.copy()
            metadatas.append(meta)

    # 生成唯一 ID
    # 注意：ID 必须在租户范围内唯一即可
    ids = [f"doc_{tenant_id}_{i}_{hash(text)}" for i, text in enumerate(texts)]
    
    if not texts:
        return

    try:
        logger.info(f"租户 {tenant_id} 正在写入向量库... 数量: {len(texts)}")
        # 计算嵌入
        embeddings = embedding_func.embed_documents(texts)
        
        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"租户 {tenant_id} 向量库写入成功！")
    except Exception as e:
        logger.error(f"向量库写入失败: {e}")
        raise e

# === 新增方法：用于混合检索（支持租户隔离） ===
def get_all_documents(tenant_id: int) -> List[Document]:
    """
    从 ChromaDB 中获取指定租户的所有文档。
    用于初始化该租户专属的 BM25Retriever。
    """
    # 关键：必须传入 tenant_id，确保只加载该租户的数据
    store = get_vectorstore(tenant_id=tenant_id)
    collection = store["collection"]
    
    count = collection.count()
    if count == 0:
        return []

    batch_size = 1000
    all_docs = []
    
    logger.info(f"正在加载租户 {tenant_id} 的文档以构建 BM25 索引，总数: {count}...")
    
    for offset in range(0, count, batch_size):
        results = collection.get(
            limit=batch_size,
            offset=offset,
            include=['documents', 'metadatas']
        )
        
        docs_list = results.get('documents', [])
        metas_list = results.get('metadatas', [])
        
        for i in range(len(docs_list)):
            doc = Document(
                page_content=docs_list[i],
                metadata=metas_list[i] if metas_list[i] is not None else {}
            )
            all_docs.append(doc)
            
    logger.info(f"成功加载租户 {tenant_id} 的 {len(all_docs)} 个文档。")
    return all_docs