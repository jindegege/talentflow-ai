# 从 SQLAlchemy 库中导入常用的字段类型定义
# Column: 定义表列
# Integer, String, Text: 数据类型
# DateTime: 时间类型
# ForeignKey: 定义外键约束，用于关联表
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

# 导入 datetime 模块，用于获取当前时间
from datetime import datetime

# 从当前包中导入 Base 对象
# Base 是 SQLAlchemy 的基类，所有模型类都需要继承它
from . import Base

from sqlalchemy.orm import relationship

import uuid

# ==========================================
# 2. 数据库模型 (ORM)
# ==========================================

# 定义租户模型类，对应数据库中的 tenants 表
# 租户是 SaaS 系统的核心概念，用于实现数据隔离
class TenantDB(Base):
    # 指定数据库表名为 "tenants"
    __tablename__ = "tenants"
    
    # 定义主键 ID 列
    # primary_key=True 表示这是主键
    # index=True 表示为该字段创建索引，加快查询速度
    id = Column(Integer, primary_key=True, index=True)
    
    # 定义租户名称列
    # String(100) 表示最大长度为 100 的字符串
    # nullable=False 表示该字段不能为空
    name = Column(String(100), nullable=False)
    
    # 定义创建时间列
    # default=datetime.now 表示插入数据时，默认为当前时间
    created_at = Column(DateTime, default=datetime.now)

# 定义用户模型类，对应数据库中的 users 表
class UserDB(Base):
    # 指定数据库表名为 "users"
    __tablename__ = "users"
    
    # 定义主键 ID 列
    id = Column(Integer, primary_key=True, index=True)
    
    # 定义租户 ID 列（外键）
    # ForeignKey("tenants.id") 表示该字段关联到 tenants 表的 id 字段
    # 这建立了用户与租户的多对一关系（一个租户有多个用户）
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    
    # 定义用户名字段
    # unique=True 表示用户名必须唯一，不能重复
    # index=True 表示创建索引，加快登录时的查询速度
    # nullable=False 表示用户名不能为空
    username = Column(String(50), unique=True, index=True, nullable=False)
    
    # 定义密码字段
    # 存储的是经过哈希加密后的字符串，不是明文密码
    # String(100) 足够存储 bcrypt 加密后的字符串
    password = Column(String(100), nullable=False)
    
    # 定义昵称字段
    # 用于前端显示，可以为空
    nickname = Column(String(50))
    
    # 定义角色字段
    # Integer 类型，例如 0 代表普通用户，1 代表管理员
    role = Column(Integer)
    
    # 定义用户创建时间
    # 默认值为当前时间
    created_at = Column(DateTime, default=datetime.now)
    
    
class KnowledgeFile(Base):
    __tablename__ = "knowledge_files"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, index=True)
    file_path = Column(String)  # 本地存储路径
    tenant_id = Column(String, index=True)  # 属于哪个公司/租户
    uploader_id = Column(String)  # 谁上传的（管理员ID）
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatSessionDB(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    tenant_id = Column(Integer, index=True)
    title = Column(String(255), comment="会话标题")
    created_at = Column(DateTime, default=datetime.utcnow)

    # 修改 1：引用正确的类名 "ChatMessageDB"
    messages = relationship("ChatMessageDB", back_populates="session", cascade="all, delete-orphan")


class ChatMessageDB(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    
    tenant_id = Column(Integer, index=True)
    
    role = Column(String(50))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 修改 2：这里也要引用正确的类名 "ChatSessionDB" (你原来写的是 "ChatSession")
    session = relationship("ChatSessionDB", back_populates="messages")