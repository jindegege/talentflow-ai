# app/core/celery_app.py
from celery import Celery

# 使用 Redis 作为消息中间件 (broker) 和结果存储 (backend)
celery_app = Celery(
    "worker",
    broker="redis://:123456@localhost:6379/0",  # 如果你的 Redis 有密码，格式为 redis://:password@localhost:6379/0
    backend="redis://:123456@localhost:6379/1"
)

# 自动发现并加载任务模块
celery_app.autodiscover_tasks(["app.tasks", "app.rag.recommendation_service"]) 