# 全局异常处理器
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging

from app.core.exceptions import AppException

logger = logging.getLogger("app")

async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常拦截器
    """
    # 1. 处理已知的业务异常
    if isinstance(exc, AppException):
        logger.warning(f"业务异常: {exc.message} | Path: {request.url.path}")
        return JSONResponse(
            status_code=exc.code,
            content={"error": exc.message, "code": exc.code}
        )
    
    # 2. 处理参数校验异常 (Pydantic/FastAPI 自带)
    if isinstance(exc, (RequestValidationError, ValidationError)):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "参数校验失败", "detail": str(exc)}
        )

    # 3. 处理未知系统异常 (兜底)
    logger.error(f"系统未捕获异常: {exc}", exc_info=True) # exc_info=True 会打印堆栈
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "系统内部错误", "code": 500}
    )

# 在 main.py 中注册
# app.add_exception_handler(Exception, global_exception_handler)