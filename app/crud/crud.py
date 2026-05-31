from typing import Optional, List
from sqlalchemy.orm import Session

# 导入模型和 Schema
from app.models import base
from app.schemas.user_schema import UserCreate
from app.core import security

# 导入用户模型模块
# 使用别名 user_model 来引用，方便后续代码调用
from app.models import user as user_model
from app.models.resume import Resume

from sqlalchemy.orm import Session as SQLASession

# ==========================================
# 用户认证模块 (Auth CRUD)
# ==========================================
def get_user_by_username(db: SQLASession, username: str) -> Optional[user_model.User]:
    """根据ID查询用户"""
    return db.query(user_model.User).filter(user_model.User.username == username).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[base.UserDB]:
    """
    根据 ID 查询用户
    """
    return db.query(user_model.User).filter(user_model.User.id == user_id).first()

def create_user(db: Session, user_in: UserCreate) -> base.UserDB:
    """
    创建新用户
    1. 使用 security 模块对密码进行哈希处理 (当前配置为 Argon2)
    2. 存入数据库
    """
    # 调用 security 模块生成哈希密码
    # 这里会自动使用你在 security.py 中配置的 argon2 算法
    hashed_password = security.get_password_hash(user_in.password)
    
    db_user = base.UserDB(
        username=user_in.username,
        password=hashed_password, # 存入加密后的哈希值
        role=0 # 默认为普通用户
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# crud.py
from sqlalchemy.orm import Session
from app.core.vector_store import add_documents_to_vectorstore
import os
from app.schemas.resume_schema import ResumeUpdate,ResumeCreate,ResumeBase

# 向量库文件路径（需与 vector_store.py 保持一致或导入）
db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "faiss_db")
index_path = os.path.join(db_dir, "index.faiss")

def concatenate_text(data: ResumeBase) -> str:
    """
    【核心策略】拼接字段：自我评价 + 工作经历 + 项目经历
    """
    parts = []
    if data.summary:
        parts.append(f"【个人评价】{data.summary}")
    if data.work_experience:
        parts.append(f"【工作经历】{data.work_experience}")
    if data.project_experience:
        parts.append(f"【项目经历】{data.project_experience}")
    
    return "\n".join(parts)

def create_resume(db: Session, resume_in: ResumeCreate):
    # 1. 拼接文本
    full_text = concatenate_text(resume_in)
    
    # 2. 先存入 MySQL (为了获取自增 ID)
    # 注意：此时 vector_id 先设为 None 或临时值
    db_resume = Resume(**resume_in.dict())
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    
    # 3. 存入 Faiss 向量库
    if full_text.strip():
        # 使用 resume_id 作为向量库的元数据 ID
        metadata = {"resume_id": db_resume.id, "title": db_resume.title or "未命名"}
        
        # 调用你提供的 Faiss 工具函数
        # 注意：你的 add_documents_to_vectorstore 接受 List[str]
        add_documents_to_vectorstore([full_text], [metadata])
        
        # 4. 更新 MySQL 中的 vector_id (可选，如果我们需要强关联)
        # 在你的 Faiss 实现中，ID 是自增的索引，我们可以认为 MySQL ID 就是向量库的索引
        # 或者如果你的 Faiss 逻辑返回了具体 ID，则更新这里
        # 这里简单处理：假设向量库顺序与 MySQL ID 对应，或者不需要回写 vector_id
        
    return db_resume

def update_resume(db: Session, db_resume: Resume, resume_in: ResumeUpdate):
    # 1. 更新 MySQL 数据
    update_data = resume_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_resume, field, value)
    
    db.commit()
    db.refresh(db_resume)
    
    # 2. 更新 Faiss (简易策略：重建该条目)
    # 注意：Faiss 不支持直接修改向量，通常是 Remove + Add
    # 你的 vector_store.py 目前没有实现 remove，这里仅做逻辑示意
    # 实际生产中，建议记录 vector_id，先删除旧向量，再添加新向量
    
    full_text = concatenate_text(resume_in)
    if full_text.strip():
        # 这里需要完善 vector_store.py 的删除功能
        # remove_document_by_id(db_resume.id) 
        # add_documents_to_vectorstore([full_text], [{"resume_id": db_resume.id}])
        pass
        
    return db_resume

def delete_resume(db: Session, resume_id: int):
    # 1. 删除 MySQL
    obj = db.query(Resume).filter(Resume.id == resume_id).first()
    if obj:
        db.delete(obj)
        db.commit()
        
    # 2. 删除 Faiss (需要 vector_store 支持)
    # remove_document_by_id(resume_id)

def get_resumes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Resume).offset(skip).limit(limit).all()
