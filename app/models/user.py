from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
import datetime

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, nullable=False, unique=True, description="登录账号")
    password: str = Field(nullable=False, description="加密后的密码")
    email: Optional[str] = Field(default=None, index=True, nullable=True, description="邮箱")
    full_name: Optional[str] = Field(default=None, description="用户昵称或真实姓名")
    is_active: Optional[bool] = Field(default=True, description="是否激活: True正常, False封禁")
    role: int = Field(nullable=False, description="角色: 0求职者, 1管理员")
    created_at: Optional[datetime.datetime] = Field(default_factory=datetime.datetime.utcnow)
    
    # --- 核心修复：User 这一侧也必须明确指定 foreign_keys ---
    
    # 1. 该用户作为“发布者”发布的任务列表
    tasks: List["Task"] = Relationship(
        back_populates="mentor",
        sa_relationship_kwargs={"foreign_keys": "[Task.mentor_id]"}
    )
    
    # 2. 该用户作为“接单者”承接的任务列表
    accepted_tasks: List["Task"] = Relationship(
        back_populates="taker",
        sa_relationship_kwargs={"foreign_keys": "[Task.taken_by]"}
    )
    
    # 3. 用户的投递记录
    applications: List["Application"] = Relationship(back_populates="owner")

    @property
    def role_label(self) -> str:
        return "管理员" if self.role == 1 else "求职者"