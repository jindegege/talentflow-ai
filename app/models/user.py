# 从 SQLModel 库导入核心组件
# SQLModel: 用于定义数据库模型的基类
# Field: 用于定义字段属性（如主键、外键、索引等）
from sqlmodel import SQLModel, Field

# 导入 Optional 类型提示，用于表示字段可以为 None
from typing import Optional

# 导入 datetime 模块，用于处理时间戳
import datetime

# 定义用户模型类
# 继承 SQLModel 以具备 ORM 功能
# table=True 表示这个类对应数据库中的一张实际存在的表
class User(SQLModel, table=True):
    # 指定数据库表名为 "users" (通常 SQLModel 会自动推断，但显式声明更规范)
    __tablename__ = "users"
    
    # 定义主键 ID 字段
    # Optional[int]: 类型提示，表示可以是整数或 None
    # default=None: 默认值为 None，由数据库自增生成
    # primary_key=True: 指定为主键
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 定义用户名字段
    # str: 字符串类型
    # index=True: 在数据库中为该列创建索引，加快查询速度
    # nullable=False: 数据库约束，该字段不能为空
    # unique=True: 数据库约束，用户名必须唯一，不可重复
    username: str = Field(index=True, nullable=False, unique=True)
    
    # 定义密码字段
    # nullable=False: 密码不能为空
    # 注意：这里存储的是经过哈希加密后的字符串，不是明文
    password: str = Field(nullable=False)
    
    # 定义昵称字段
    # default=None: 默认值为 None（即数据库中的 NULL），允许不填
    nickname: str = Field(default=None)
    
    # 定义角色字段
    # role: 用于区分管理员、普通用户等
    # nullable=False: 角色字段不能为空
    role: int = Field(nullable=False)
    
    # 定义创建时间字段
    # default_factory=datetime.datetime.utcnow: 每次创建新对象时，自动调用该函数获取当前 UTC 时间
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    
    # 定义租户 ID 字段（外键）
    # Optional[int]: 可以是整数或 None
    # default=None: 默认为空
    # foreign_key="tenant.id": 指定外键约束，关联到 tenant 表的 id 字段
    # 注意：这里只定义了物理外键字段，没有使用 SQLModel 的 Relationship 对象
    # 这样做的好处是避免了多表关联时的循环导入问题，适合简单的 CRUD 操作
    tenant_id: Optional[int] = Field(default=None, foreign_key="tenant.id")