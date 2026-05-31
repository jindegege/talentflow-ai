# app\models\base.py
from sqlalchemy import Column, Integer, String, Text, DateTime,SmallInteger, ForeignKey, Boolean, func
from sqlalchemy.orm import relationship, declarative_base

# 从当前包导入 Base 类（如果你的项目混用了 SQLAlchemy 原生写法）
from . import Base


# ==========================================
# 2. 用户表模型
# ==========================================
class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="candidate")  # candidate, admin, hr
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    full_name = Column(String(50), unique=True, nullable=True)

    # 关联关系
    resumes = relationship("ResumeDB", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("ApplicationDB", back_populates="user")
    sessions = relationship("ChatSessionDB", back_populates="user", cascade="all, delete-orphan")
    deliveries = relationship("TaskDeliveryDB", back_populates="user")


# ==========================================
# 3. 技能字典表模型
# ==========================================
class SkillDB(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    category = Column(String(30), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("skills.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ==========================================
# 4. 简历表模型
# ==========================================
class ResumeDB(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(100), nullable=False)
    summary = Column(Text, nullable=True)
    project_experience = Column(Text, nullable=True)
    education = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    vector_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系
    user = relationship("UserDB", back_populates="resumes")
    applications = relationship("ApplicationDB", back_populates="resume")


# ==========================================
# 5. 职位表模型
# ==========================================
class JobDB(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    company = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(50), nullable=True)
    salary_range = Column(String(50), nullable=True)
    source_url = Column(String(255), nullable=True)
    vector_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    applications = relationship("ApplicationDB", back_populates="job")


# ==========================================
# 6. 投递记录表模型
# ==========================================
class ApplicationDB(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    status = Column(String(20), default="applied")
    cover_letter = Column(Text, nullable=True)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    user = relationship("UserDB", back_populates="applications")
    job = relationship("JobDB", back_populates="applications")
    resume = relationship("ResumeDB", back_populates="applications")


# ==========================================
# 7. 实战任务表模型 (项目管理核心)
# ==========================================
class TaskDB(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    # 基础信息
    title = Column(String(150), nullable=False, comment="任务标题")
    description = Column(Text, nullable=True, comment="任务简短描述/摘要")

    # 详细内容 (通常存储HTML或Markdown)
    content = Column(Text, nullable=True, comment="任务详细描述，包含需求、步骤等")

    # 属性
    required_skills = Column(String(255), nullable=True, comment="推荐技能标签，逗号分隔")
    difficulty = Column(String(20), default="Intermediate", comment="难度等级: Beginner, Intermediate, Advanced")

    # 状态控制
    is_active = Column(Boolean, default=True, comment="是否上架/激活")
    status = Column(String(20), default="active", comment="逻辑状态: active, archived, draft")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关联关系
    deliveries = relationship("TaskDeliveryDB", back_populates="task", cascade="all, delete-orphan")


# ==========================================
# 8. 任务交付表模型
# ==========================================
class TaskDeliveryDB(Base):
    __tablename__ = "task_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    delivery_url = Column(String(255), nullable=True, comment="交付物链接，如GitHub地址")
    comment = Column(Text, nullable=True, comment="用户备注")
    status = Column(String(20), default="submitted", comment="submitted, reviewed, rejected")
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    task = relationship("TaskDB", back_populates="deliveries")
    user = relationship("UserDB", back_populates="deliveries")


# ==========================================
# 9. AI 聊天会话表模型
# ==========================================
class ChatSessionDB(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(100), default="新对话")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    user = relationship("UserDB", back_populates="sessions")
    messages = relationship("ChatMessageDB", back_populates="session", cascade="all, delete-orphan")


# ==========================================
# 10. AI 聊天消息表模型
# ==========================================
class ChatMessageDB(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联关系
    session = relationship("ChatSessionDB", back_populates="messages")
    

class ProjectDB(Base):
    """项目表 ORM 模型"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, comment="项目ID")
    title = Column(String(255), nullable=False, comment="项目标题")
    category = Column(String(50), nullable=False, comment="项目分类")
    reward = Column(String(50), nullable=False, comment="悬赏积分")
    level = Column(String(50), nullable=False, comment="等级")
    description = Column(Text, comment="项目详细描述")
    status = Column(SmallInteger, default=1, comment="项目状态：0-已关闭，1-招募中，2-进行中，3-已完成")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")