# 从 fastapi 库中导入 FastAPI 类，用于创建应用实例
from fastapi import FastAPI

# 导入 CORS 中间件，用于处理浏览器的跨域资源共享请求
from fastapi.middleware.cors import CORSMiddleware

# 从 app.api.v1 包中导入 auth 模块（即路由文件）
from app.api.v1 import auth,upload,chat

import sys
import asyncio

from app.core.middleware import global_exception_handler

# --- 【核心修复】强制 Windows 使用旧版网络策略 ---
if sys.platform == "win32":
    print('win32----')
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 创建一个 FastAPI 应用实例
# title 参数定义了 API 文档（Swagger UI）的标题
app = FastAPI(title="SaaS RAG 业务系统")

# ==========================================
# 配置跨域资源共享 (CORS) 中间件
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 允许所有来源的跨域请求（生产环境建议指定具体域名）
    allow_credentials=True,       # 允许跨域请求携带 Cookie 或认证信息
    allow_methods=["*"],          # 允许所有 HTTP 方法（GET, POST, PUT, DELETE 等）
    allow_headers=["*"],          # 允许所有 HTTP 请求头
)

# ==========================================
# 注册路由
# ==========================================
# 将 auth 模块中的路由注册到主应用中
# prefix="/api/v1/auth" 为所有路由添加了统一的前缀
# 例如：auth.py 中的 @router.post("/login") 将自动变为 /api/v1/auth/login
# tags=["认证"] 用于在 API 文档中对接口进行分组显示
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(upload.router,prefix="/api/v1", tags=["上传"])
app.include_router(chat.router,prefix="/api/v1", tags=["会话"])
app.add_exception_handler(Exception, global_exception_handler)
# ==========================================
# 根路径健康检查
# ==========================================
@app.get("/")
def root():
    # 当用户访问网站根目录时，返回欢迎信息
    return {"message": "Welcome to SaaS RAG API"}
