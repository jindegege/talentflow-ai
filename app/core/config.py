# 导入 os 模块，用于读取操作系统的环境变量
import os

from pydantic import ConfigDict

# 从 python-dotenv 库中导入 load_dotenv 函数
# 这个函数的作用是从 .env 文件中加载环境变量到系统环境中
from dotenv import load_dotenv

# 执行 load_dotenv()，加载项目根目录下 .env 文件中的配置
# 这样代码中就可以通过 os.getenv() 读取 .env 里的变量了
load_dotenv()

# 定义一个 Settings 类，用于集中管理项目的配置信息
class Settings:
        # 数据库配置
    # 默认值设为 'db'，因为我们在 docker-compose 中会将 MySQL 服务命名为 db
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "db")
    MYSQL_PORT: int = os.getenv("MYSQL_PORT", 3306)
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "password")
    MYSQL_DB: str = os.getenv("MYSQL_DB", "smart_cs")

    # 向量库配置
    # 同样，ChromaDB 的服务名在 compose 中叫 vector_db
    CHROMA_DB_HOST: str = os.getenv("CHROMA_DB_HOST", "vector_db")
    CHROMA_DB_PORT: int = os.getenv("CHROMA_DB_PORT", 8000)
    def __init__(self):
        # 强制从 .env 文件读取，忽略系统环境变量
        from dotenv import dotenv_values
        env_vars = dotenv_values(".env")  # 读取 .env 文件内容
        
        # 打印 .env 文件里的 Key（用于调试）
        # print("Debug - .env 文件中的 OPENAI_API_KEY:", env_vars.get("OPENAI_API_KEY"))
        
        # 强制使用 .env 里的值，或者如果不存在则报错
        self.API_KEY = env_vars.get("OPENAI_API_KEY", "")
        
        if not self.API_KEY:
            raise ValueError("未在 .env 文件中找到 OPENAI_API_KEY！")
    # 定义 JWT 的密钥，用于签名和验证 Token
    # os.getenv("SECRET_KEY", "fallback_secret") 表示：
    # 1. 尝试读取环境变量中的 SECRET_KEY
    # 2. 如果读取不到（例如 .env 文件缺失），则使用默认值 "fallback_secret"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback_secret")
    
    # 定义 JWT 的加密算法，默认使用 HS256
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    
    # 定义 Token 的过期时间，单位为分钟，默认 30 分钟
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    
    PROJECT_ROOT: str = r"E:\project\smart-customer\smart-cs-backend"
    
    # 向量库路径
    VECTOR_DB_PATH: str = os.path.join(PROJECT_ROOT, "chroma_db")
    
    # 集合名称
    CHROMA_COLLECTION_NAME: str = "rag_collection"
    
    model_config = ConfigDict(extra="ignore")
    
    API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    


# 实例化 Settings 类，创建一个全局的 settings 对象
# 其他模块可以直接导入这个对象来使用配置，例如：from app.core.config import settings
settings = Settings()