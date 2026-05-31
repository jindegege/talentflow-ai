# backend/app/rag/embedding.py
# 负责将文本转化为向量

import logging
from langchain_huggingface import HuggingFaceEmbeddings

def get_embedding_function():
    """
    获取本地嵌入模型实例
    """
    # 你的本地模型路径
    local_model_path = r"E:\llm\BAAI\bge-small-zh-v1.5"
    
    # 核心修复：降低 transformers 库的日志级别，过滤掉 UNEXPECTED 警告
    logging.getLogger("transformers").setLevel(logging.ERROR)
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    
    print(f"正在加载本地 Embedding 模型: {local_model_path} ...")
    
    # 2. 初始化配置
    model_kwargs = {
        'device': 'cpu',  # 如果你有 NVIDIA 显卡，可以改为 'cuda'
        'trust_remote_code': True,  # BGE 模型必须开启
        'local_files_only': True     # 强制离线加载，避免网络请求
    }
    
    encode_kwargs = {
        'normalize_embeddings': True, # BGE 模型建议开启归一化
        'batch_size': 32
    }

    # 3. 返回模型实例
    embeddings = HuggingFaceEmbeddings(
        model_name=local_model_path, 
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
    
    print("本地 Embedding 模型加载成功！")
    return embeddings