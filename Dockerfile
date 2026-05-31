# smart-cs-backend/Dockerfile

# 1. 使用 Python 官方镜像
FROM python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 设置环境变量（避免 Python 生成 .pyc 文件，且日志实时输出）
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. 安装系统依赖（如果需要编译某些库，如 gcc）
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# 5. 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. 复制项目源码
COPY . .

# 7. 暴露端口（假设 FastAPI 运行在 8000）
EXPOSE 8000

# 8. 启动命令
# 使用 uvicorn 启动，0.0.0.0 表示允许外部访问
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]