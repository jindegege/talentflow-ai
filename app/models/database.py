# 文件路径：app/database.py
# 作用：数据库连接配置、引擎初始化、会话管理及表创建

# 从 SQLModel 库导入核心组件
# SQLModel: 结合了 SQLAlchemy 和 Pydantic 的 ORM 库
# create_engine: 创建数据库连接引擎
# Session: 用于与数据库交互的会话类
from sqlmodel import SQLModel, create_engine, Session

# 从 SQLAlchemy 导入 sessionmaker，用于配置会话工厂
from sqlalchemy.orm import sessionmaker


# 导入 os 模块，用于读取环境变量
import os

# 导入 load_dotenv 以加载 .env 文件中的配置
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# ==========================================
# 数据库连接配置
# ==========================================

# 从环境变量中读取数据库连接 URL
# 格式通常为： dialect+driver://username:password@host:port/database
# 如果环境变量未设置，则使用默认的 SQLite 或 MySQL 连接字符串作为兜底
# 注意：原代码中混用了 MySQL 和 SQLite 的配置逻辑，建议根据实际使用的数据库二选一
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:123456@localhost:3306/dandelion_tribe?charset=utf8mb4")

# 创建数据库引擎
# echo=False 表示不在控制台打印生成的 SQL 语句（开发调试时可设为 True）
engine = create_engine(DATABASE_URL, echo=False)

# 创建会话工厂
# autocommit=False: 不自动提交事务，需要手动 commit
# autoflush=False: 不自动刷新数据
# bind=engine: 绑定到上面创建的引擎
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ==========================================
# 依赖注入：获取数据库会话
# ==========================================

# 定义一个生成器函数，用于 FastAPI 的 Depends 依赖注入
# 每次请求都会创建一个新的数据库会话，请求结束后自动关闭
def get_db():
    db = SessionLocal() # 创建会话实例
    try:
        yield db        # 将会话提供给接口使用
    finally:
        db.close()      # 确保会话被关闭，释放连接

# ==========================================
# 初始化与工具函数
# ==========================================

# 确保项目根目录下存在 data 目录（通常用于存放 SQLite 文件或上传的文件）
os.makedirs("./data", exist_ok=True)

# 定义 SQLite 特有的连接参数
# check_same_thread=False 允许在 FastAPI 的多线程环境中访问 SQLite 数据库
# 注意：这仅在使用 SQLite 时有效，MySQL/PostgreSQL 不需要此参数
connect_args = {"check_same_thread": False}

def create_db_and_tables():
    """
    初始化数据库表结构
    必须在应用启动时调用，确保模型被注册并创建对应的表
    """
    # 必须在这里导入 models 模块
    # 原因：SQLModel 需要在元数据中注册所有模型类，如果不在函数内部导入，
    # 可能会因为循环引用或执行顺序问题导致表无法创建
    from app import models 
    
    # 根据导入的模型定义，在数据库中创建所有表（如果表不存在）
    SQLModel.metadata.create_all(engine)
    print("数据库表已检查/创建完成")

def get_session():
    """
    获取 SQLModel 风格的数据库会话
    这是 SQLModel 推荐的依赖注入写法，配合 with 语句使用
    """
    with Session(engine) as session:
        yield session