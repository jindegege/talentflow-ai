import os
from typing import List
from langchain_core.documents import Document

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

# 1. 配置本地模型路径
MODEL_PATH = r"E:\llm\BAAI\bge-reranker-v2-m3"

class Reranker:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"模型文件未找到: {MODEL_PATH}")
        
        print(f"正在加载重排序模型 (CPU模式): {MODEL_PATH}")
        
        # 2. 初始化模型 (CPU 关键配置)
        # device='cpu': 强制使用 CPU，不检测显卡
        # use_fp16=False: CPU 不支持半精度加速，必须设为 False，否则可能报错或更慢
        self.reranker = FlagReranker(MODEL_PATH, device='cpu', use_fp16=False)
        
        print("重排序模型加载完毕 (运行在 CPU 上)！")

    def rank(self, query: str, documents: List[Document], top_k: int = 3):
        """
        对文档列表进行重排序
        """
        if not documents:
            return []

        # 3. 准备数据对
        pairs = [[query, doc.page_content] for doc in documents]
        
        # 4. 计算分数
        # CPU 模式下计算速度取决于你的 CPU 核心数
        # 强制返回 float 列表，防止新版返回 numpy 或 tensor 导致排序报错
        scores = self.reranker.compute_score(pairs, normalize=True) 

        # 如果是批量处理，确保它是列表
        if isinstance(scores, float): 
            scores = [scores]
        
        # 5. 绑定并排序
        doc_score_pairs = list(zip(documents, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # 6. 截取 Top K
        top_docs = [doc for doc, score in doc_score_pairs[:top_k]]
        
        # 调试日志
        print(f"重排序完成：从 {len(documents)} 篇文档中筛选出 {top_k} 篇。")
        for i, (doc, score) in enumerate(doc_score_pairs[:top_k]):
            print(f"   Top {i+1}: 分数={score:.4f}, 内容={doc.page_content[:30]}...")
            
        return top_docs

# 全局单例
global_reranker = Reranker()