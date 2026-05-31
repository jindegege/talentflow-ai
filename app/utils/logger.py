import logging
import os

# 确保日志目录存在
os.makedirs("logs", exist_ok=True)

# 创建一个自定义的 logger
logger = logging.getLogger("rag_app")
logger.setLevel(logging.INFO)

# 防止重复添加 handler
if not logger.handlers:
    # ==========================================
    # 核心修复：禁用控制台输出 (StreamHandler)
    # 既然 Windows 控制台一直报 ascii 错误，我们直接不让它往控制台写
    # ==========================================
    
    # 1. 创建一个文件处理器 (写入 logs/app.log)
    # 这里显式指定 encoding='utf-8'，确保文件里中文正常
    file_handler = logging.FileHandler('logs/app.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 2. 设置格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # 3. 添加处理器
    logger.addHandler(file_handler)
    
    # 【关键】：不要添加 StreamHandler，这样就不会有 ascii 报错打断程序了
    # 如果你想看日志，去查看项目目录下的 logs/app.log 文件