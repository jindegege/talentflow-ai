from sqlalchemy.orm import Session
from typing import List, Optional
from app.models import base
from app.schemas import message_schema # 假设你有对应的 Pydantic 模型
from datetime import datetime

# ==========================================
# 1. 创建消息 (核心归档逻辑)
# ==========================================
def create_message(
    db: Session, 
    thread_id: str, 
    user_id: int, 
    role: str, 
    content: str,
    meta_data: Optional[dict] = None
):
    """
    保存单条消息到数据库
    用于对话结束后的异步归档
    """
    db_message = base.MessageDB(
        thread_id=thread_id,
        user_id=user_id,
        role=role,           # "user" 或 "assistant"
        content=content,
        meta_data=meta_data, # 可选：存储 token 消耗、模型名称等
        created_at=datetime.now()
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

# ==========================================
# 2. 获取会话历史
# ==========================================
def get_messages_by_thread(
    db: Session, 
    thread_id: str, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100
):
    """
    获取指定会话的历史记录
    增加了 user_id 校验，防止越权访问
    """
    return db.query(base.MessageDB)\
             .filter(base.MessageDB.thread_id == thread_id)\
             .filter(base.MessageDB.user_id == user_id)\
             .order_by(base.MessageDB.created_at.asc())\
             .offset(skip)\
             .limit(limit)\
             .all()

# ==========================================
# 3. 获取单条消息
# ==========================================
def get_message(db: Session, message_id: int, user_id: int):
    """
    获取单条消息详情
    """
    return db.query(base.MessageDB)\
             .filter(base.MessageDB.id == message_id)\
             .filter(base.MessageDB.user_id == user_id)\
             .first()

# ==========================================
# 4. 批量删除会话消息
# ==========================================
def delete_messages_by_thread(db: Session, thread_id: str, user_id: int):
    """
    清空某个会话的所有消息
    通常在用户点击“清空会话”时调用
    """
    count = db.query(base.MessageDB)\
              .filter(base.MessageDB.thread_id == thread_id)\
              .filter(base.MessageDB.user_id == user_id)\
              .delete()
    
    db.commit()
    return count > 0