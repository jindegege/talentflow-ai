# api/v1/__init__.py

# 1. 导入子模块的路由对象 (假设你在两个文件里都定义了 router)
from .auth import router as auth_router
from .upload import router as upload_router


# 创建一个聚合的主 router (更推荐)
from fastapi import APIRouter

router = APIRouter(prefix="/v1")
router.include_router(auth_router, prefix="/auth", tags=["认证"])
router.include_router(upload_router, prefix="/upload", tags=["上传"])