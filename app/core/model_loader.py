# app/core/model_loader.py
from sentence_transformers import SentenceTransformer

import transformers

# --- 修复补丁开始 ---
# 检查当前版本是否缺失该函数，如果缺失则手动补上
if not hasattr(transformers.utils, "is_torch_fx_available"):
    print("正在自动修复 transformers 兼容性缺失...")

    # 1. 定义一个假的检查函数（默认返回 False，即不使用 Torch FX）
    def _mock_is_torch_fx_available():
        return False

    # 2. 将这个函数动态注入到 transformers.utils 中
    transformers.utils.is_torch_fx_available = _mock_is_torch_fx_available

    # 3. 同时修补 import_utils（防止 FlagEmbedding 从旧路径引用报错）
    if not hasattr(transformers.utils, "import_utils"):
        import types
        transformers.utils.import_utils = types.ModuleType("import_utils")
    transformers.utils.import_utils.is_torch_fx_available = _mock_is_torch_fx_available

    print("修复完成，继续运行...")
# --- 修复补丁结束 ---

from FlagEmbedding import FlagReranker
import os
import traceback

# 定义路径
EMBEDDING_MODEL_PATH = r"E:\llm\BAAI\bge-small-zh-v1.5"
RERANKER_MODEL_PATH = r"E:\llm\BAAI\bge-reranker-v2-m3"

# 全局变量
embedding_model = None
reranker_model = None

def load_all_models():
    global embedding_model, reranker_model
    print("正在加载 AI 模型到内存...")

    # 1. 加载向量模型
    try:
        if os.path.exists(EMBEDDING_MODEL_PATH):
            embedding_model = SentenceTransformer(EMBEDDING_MODEL_PATH)
            print("向量模型加载完成")
        else:
            print(f"向量模型路径不存在: {EMBEDDING_MODEL_PATH}")
    except Exception as e:
        print(f"向量模型加载失败: {e}")
        print(traceback.format_exc()) # 打印完整报错堆栈

    # 2. 加载重排序模型 (重点排查这里)
    try:
        if os.path.exists(RERANKER_MODEL_PATH):
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            use_fp16 = (device == "cuda")
            
            print(f"正在加载重排序模型 (设备: {device.upper()}, FP16: {use_fp16})...")
            # 这里最容易报错，比如 transformers 版本不兼容、模型文件损坏等
            reranker_model = FlagReranker(RERANKER_MODEL_PATH, device=device, use_fp16=use_fp16)
            print("重排序模型加载完成")
        else:
            print(f"重排序模型路径不存在: {RERANKER_MODEL_PATH}")
    except Exception as e:
        print(f"重排序模型加载失败: {e}")
        print(traceback.format_exc()) # 打印完整报错堆栈，这能直接告诉你缺了什么

def get_embedding_model():
    return embedding_model

def get_reranker_model():
    return reranker_model

def check_cuda():
    """简单检查是否有可用的 CUDA"""
    try:
        import torch
        return torch.cuda.is_available()
    except:
        return False