import os
import faiss
import numpy as np
import pickle
from typing import Dict, List
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from app.utils.logger import logger

# 你的本地模型路径
local_model_path = r"E:\llm\BAAI\bge-small-zh-v1.5"
# 数据库路径
db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "faiss_db")
index_path = os.path.join(db_dir, "index.faiss")
metadata_path = os.path.join(db_dir, "index_metadata.pkl")

def get_embedding_function():
    """获取 Embedding 模型"""
    model_kwargs = {'device': 'cpu', 'trust_remote_code': True, 'local_files_only': True}
    # 关键：必须归一化，这样内积(IP)才等于余弦相似度
    encode_kwargs = {'normalize_embeddings': True, 'batch_size': 32}
    
    return HuggingFaceEmbeddings(
        model_name=local_model_path,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )

def get_vectorstore() -> Dict:
    """
    获取 FAISS 向量库实例
    修复点：使用 IndexFlatIP 代替 IndexFlatL2 以支持余弦相似度
    """
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        logger.info(f"创建向量库目录: {db_dir}")

    embedding_func = get_embedding_function()
    dimension = 512 

    if os.path.exists(index_path):
        logger.info(f"加载现有 FAISS 索引: {index_path}")
        index = faiss.read_index(index_path)
        
        if os.path.exists(metadata_path):
            with open(metadata_path, "rb") as f:
                metadatas = pickle.load(f)
        else:
            logger.warning("元数据文件丢失，初始化为空")
            metadatas = []
            
    else:
        logger.info("初始化新的 FAISS 索引 (使用 Inner Product 用于余弦相似度)...")
        # 核心修复：使用 IndexFlatIP (Inner Product)
        # 对于归一化向量，IP = Cosine Similarity
        # index = faiss.IndexFlatIP(dimension) 
        index = faiss.IndexHNSWFlat(dimension, 32) 
        metadatas = []

    return {
        "index": index,
        "embedding_function": embedding_func,
        "metadatas": metadatas,
        "dimension": dimension
    }

def add_documents_to_vectorstore(documents: List[str], metadatas: List[Dict]):
    """
    添加文档到 FAISS
    """
    if not documents:
        return

    store = get_vectorstore()
    index = store["index"]
    embedding_func = store["embedding_function"]

    logger.info(f"正在计算向量...")
    vectors = embedding_func.embed_documents(documents)
    vectors_np = np.array(vectors).astype('float32')

    # 写入索引
    index.add(vectors_np)
    
    # 更新元数据
    store["metadatas"].extend(metadatas)

    # 保存
    faiss.write_index(index, index_path)
    with open(metadata_path, "wb") as f:
        pickle.dump(store["metadatas"], f)
        
    logger.info(f"FAISS 索引保存成功，总数: {index.ntotal}")

def get_all_documents() -> List[Document]:
    """
    读取所有文档（主要用于调试）
    """
    store = get_vectorstore()
    metadatas = store["metadatas"]
    
    docs = []
    for meta in metadatas:
        # 因为我们没在 metadata 里存大段文本，这里只返回元数据摘要
        title = meta.get('title', 'Unknown')
        docs.append(Document(page_content=f"职位: {title}", metadata=meta))
    return docs