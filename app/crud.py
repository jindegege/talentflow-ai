# 从 typing 模块导入 Optional 类型
# 用于类型提示，表示函数返回值可能是 user_model.User 对象，也可能是 None
from typing import Optional

# 导入用户模型模块
# 使用别名 user_model 来引用，方便后续代码调用
from app.models import user as user_model

# 从 SQLAlchemy 导入 Session 类型
# 使用别名 SQLASession 避免与函数名或其他变量冲突
# 用于定义函数参数 db 的类型，确保 IDE 能正确提示代码
from sqlalchemy.orm import Session as SQLASession

from sqlalchemy.orm import Session
from app.models import base
from app import schemas
from app.core import security # 引入安全模块用于密码哈希


# 定义根据用户名查询用户的函数
def get_user_by_username(db: SQLASession, username: str) -> Optional[user_model.User]:
    """
    根据用户名查询用户
    使用 SQLAlchemy 的标准 query 写法
    """
    # 1. db.query(user_model.User): 构建针对 User 表的查询对象
    # 2. .filter(user_model.User.username == username): 添加过滤条件，查找 username 等于传入参数的记录
    # 3. .first(): 执行查询并只返回匹配的第一条记录
    # 如果没有找到记录，.first() 会自动返回 None
    return db.query(user_model.User).filter(user_model.User.username == username).first()

def get_user_by_id(db: SQLASession, user_id: int) -> Optional[user_model.User]:
    """根据ID查询用户"""
    return db.query(user_model.User).filter(user_model.User.id == user_id).first()

def create_user(db: Session, user_in: schemas.UserCreate, tenant_id: int):
    hashed_password = security.get_password_hash(user_in.password)
    db_user = base.UserDB(
        username=user_in.username,
        password=hashed_password,
        tenant_id=tenant_id, # 这里必须赋值
        role=0 # 默认为普通用户
        # nickname=user_in.nickname
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


from sqlalchemy.orm import Session


# ==========================================
# 1. 获取用户的所有会话 (左侧列表)
# ==========================================
def get_user_sessions(db: Session, user_id: int):
    """
    获取指定用户的所有会话，按创建时间倒序排列
    这个数据直接返回给前端的 fetchSessions
    """
    return db.query(base.ChatSessionDB)\
             .filter(base.ChatSessionDB.user_id == user_id)\
             .order_by(base.ChatSessionDB.created_at.desc())\
             .all()

# ==========================================
# 2. 获取会话下的所有消息 (右侧内容)
# ==========================================
def get_messages_by_session(db: Session, session_id: int):
    """
    获取指定会话 ID 下的所有消息，按时间顺序排列
    这个数据直接返回给前端的 fetchMessages
    """
    return db.query(base.ChatMessageDB)\
             .filter(base.ChatMessageDB.session_id == session_id)\
             .order_by(base.ChatMessageDB.created_at.asc())\
             .all()

# ==========================================
# 3. 辅助函数：验证会话归属 (防止越权)
# ==========================================
def get_session_by_id(db: Session, session_id: int, user_id: int):
    """
    检查该会话是否属于该用户
    """
    return db.query(base.ChatSessionDB)\
             .filter(base.ChatSessionDB.id == session_id, 
                     base.ChatSessionDB.user_id == user_id)\
             .first()

# ==========================================
# 4. 创建新会话
# ==========================================
def create_session(db: Session, user_id: int, title: str = "新对话"):
    db_session = base.ChatSessionDB(user_id=user_id, title=title)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

# ==========================================
# 5. 保存新消息
# ==========================================
def add_message(db: Session, session_id: int, role: str, content: str):
    db_msg = base.ChatMessageDB(session_id=session_id, role=role, content=content)
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg

# 假设你的 User 模型或者是 Pydantic schema 在这里
# from . import schemas 

def delete_session(
    db: Session, 
    session_id: int, 
    current_user: base.UserDB # 这里传入完整的用户对象
):
    """
    删除指定会话（及其关联的消息）
    """
    # 1. 查找会话，同时校验权限（必须是该用户且在该租户下）
    db_session = db.query(base.ChatSessionDB).filter(
        base.ChatSessionDB.id == session_id,
        base.ChatSessionDB.user_id == current_user.id,
        base.ChatSessionDB.tenant_id == current_user.tenant_id
    ).first()

    if not db_session:
        return None

    # 2. 执行删除
    # 注意：由于 ChatSessionDB 中定义了 cascade="all, delete-orphan"
    # 删除 session 时，数据库会自动删除关联的 chat_messages
    db.delete(db_session)
    db.commit()
    
    return db_session
