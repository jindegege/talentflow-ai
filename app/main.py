from fastapi import FastAPI
from contextlib import asynccontextmanager
# 导入路由
from app.api.v1 import auth
from app.api.v1.admin import project,jobs_manager,user_manager,resume_manager,stats_router
from app.api.v1.user import tasks,job_recommendation,smart_deliver,resumes,applications
from app.api.v1.mentor import candidate_deliver,mentor,task

# 导入 CORS 中间件，用于处理浏览器的跨域资源共享请求
from fastapi.middleware.cors import CORSMiddleware

from app.core.model_loader import load_all_models

import os

# 确保环境变量已加载
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# 1. 定义 lifespan (这是新版唯一正确的写法)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("系统正在启动...")
        # 在这里调用模型加载！
    try:
        load_all_models()
    except Exception as e:
        print(f"模型加载发生严重错误: {e}")
    print("系统启动完成，准备接收请求！")
    print("正在连接数据库...")
    # 初始化逻辑...
    yield
    print("正在关闭连接...")
    # 清理逻辑...

# 2. 创建 app 实例，传入 lifespan
app = FastAPI(title="AI蒲公英部落", lifespan=lifespan)

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

# 3. 注册路由 (注意：这里不要传任何额外参数)
app.include_router(auth.router)  
app.include_router(tasks.router)     
app.include_router(project.router) 
app.include_router(jobs_manager.router) 
app.include_router(user_manager.router) 
app.include_router(resume_manager.router) 
app.include_router(tasks.router) 
app.include_router(job_recommendation.router) 
app.include_router(smart_deliver.router) 
app.include_router(resumes.router) 
app.include_router(stats_router.router) 
app.include_router(candidate_deliver.router) 
app.include_router(mentor.router) 
app.include_router(task.router) 
app.include_router(applications.router) 

@app.get("/")
async def root():
    return {"message": "Hello World"}
