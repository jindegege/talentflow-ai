# 导入 datetime 模块，用于处理日期和时间（如计算 Token 过期时间）
from datetime import datetime, timedelta

# 导入类型提示工具，用于定义函数参数的类型
from typing import Any, Union

# 导入 python-jose 库，用于生成和解析 JWT (JSON Web Tokens)
from jose import jwt

# 导入 passlib 库，用于处理密码的哈希加密与验证
from passlib.context import CryptContext

# 从项目的配置模块中导入 settings 对象，用于获取密钥等配置信息
from app.core.config import settings

# 创建一个密码加密上下文对象
# schemes=["bcrypt"] 指定使用 bcrypt 算法进行加密（安全性高）
# deprecated="auto" 自动处理旧版本加密格式的兼容
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 定义生成 Access Token 的函数
# subject: 令牌的主题，通常是用户的 ID 或用户名
# expires_delta: 可选的过期时间增量，如果不传则使用默认配置
def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    # 如果指定了过期时间增量
    if expires_delta:
        # 过期时间 = 当前 UTC 时间 + 增量时间
        expire = datetime.utcnow() + expires_delta
    else:
        # 否则使用配置文件中定义的默认过期时间（如 30 分钟）
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # 构建 JWT 的 payload（负载）部分
    # "exp": 过期时间，JWT 会自动校验这个字段
    # "sub": 主题，用于存储用户标识，后续可以通过它查出用户
    to_encode = {"exp": expire, "sub": str(subject)}
    
    # 使用配置的密钥和算法对数据进行编码，生成最终的 JWT 字符串
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    # 返回生成的 Token
    return encoded_jwt

# 定义验证密码的函数
# plain_password: 用户登录时输入的明文密码
# hashed_password: 数据库中存储的哈希密码
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # 使用 bcrypt 算法比对明文密码和哈希密码
    # 如果匹配返回 True，否则返回 False
    return pwd_context.verify(plain_password, hashed_password)

# 定义生成密码哈希的函数
# password: 用户注册时输入的明文密码
def get_password_hash(password: str) -> str:
    # 使用 bcrypt 算法将明文密码转换为哈希字符串
    # 数据库中只存储这个哈希值，不存储明文
    return pwd_context.hash(password)