import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
from langchain_core.documents import Document

from app.core.config import settings
from app.rag.embedding import get_embedding_function
from app.utils.logger import logger

# 全局单例
_chroma_client = None
_collection = None

def get_vectorstore():
    """
    获取向量数据库单例
    """
    global _chroma_client, _collection
    
    if _chroma_client is not None and _collection is not None:
        print("使用已存在的向量数据库连接")
        return {
            "client": _chroma_client,
            "collection": _collection,
            "embedding_function": get_embedding_function()
        }

    try:
        embedding_func = get_embedding_function()
        db_path = settings.VECTOR_DB_PATH
        
        if not os.path.exists(db_path):
            os.makedirs(db_path, exist_ok=True)
            logger.info(f"创建向量库目录: {db_path}")

        # 初始化客户端 (新版本写法)
        _chroma_client = chromadb.PersistentClient(
            path=db_path, 
            settings=Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )

        _collection = _chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"向量数据库初始化成功: {_collection}")

        return {
            "client": _chroma_client,
            "collection": _collection,
            "embedding_function": embedding_func
        }
        
    except Exception as e:
        print(f"向量数据库初始化失败: {e}")
        raise

def add_documents_to_vectorstore(documents: List):
    """
    批量添加文档
    """
    store = get_vectorstore()
    collection = store["collection"]
    embedding_func = store["embedding_function"]
    
    texts = []
    metadatas = []
    
    for doc in documents:
        if isinstance(doc, dict):
            texts.append(doc.get('content', ''))
            metadatas.append(doc.get('metadata', {}))
        else:
            texts.append(doc.page_content)
            metadatas.append(doc.metadata.copy())
    
    # 生成 ID (简单哈希，实际项目建议用 UUID)
    ids = [f"doc_{i}_{abs(hash(text))}" for i, text in enumerate(texts)]
    
    try:
        # ChromaDB 的 add 方法内部会自动调用 embedding，无需手动计算
        collection.add(
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        logger.info(f"成功写入 {len(texts)} 个文档")
    except Exception as e:
        logger.error(f"写入失败: {e}")
        raise e