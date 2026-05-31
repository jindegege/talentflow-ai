import tiktoken

def count_tokens(text: str, model: str = "gpt-3.5-turbo"):
    """计算文本的 Token 数量"""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

def truncate_text(text: str, max_tokens: int = 3000):
    """简单截断文本（实际生产中建议使用滑动窗口或摘要压缩）"""
    if count_tokens(text) <= max_tokens:
        return text
    
    # 暴力截断（可能会切断句子，建议优化为按字符或句号截断）
    # 这里为了演示简单，按比例缩减
    ratio = max_tokens / count_tokens(text)
    return text[:int(len(text) * ratio)] + "...(内容过长已截断)"