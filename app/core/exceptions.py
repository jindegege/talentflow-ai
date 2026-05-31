# 自定义异常类
class AppException(Exception):
    """应用基础异常"""
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
        super().__init__(self.message)

class KnowledgeBaseEmptyError(AppException):
    """知识库为空异常"""
    def __init__(self, message: str = "当前租户未上传任何知识库文档"):
        super().__init__(message, code=400)

class RAGRetrievalError(AppException):
    """检索失败异常"""
    def __init__(self, message: str = "向量检索服务异常"):
        super().__init__(message, code=503)