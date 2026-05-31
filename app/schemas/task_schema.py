from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# ---------------------------------------------------------
# 1. 基础用户模型 (用于嵌套返回)
# ---------------------------------------------------------
class UserBase(BaseModel):
    id: int
    username: str
    # 如果需要显示全名
    # full_name: Optional[str] = None

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# 2. 任务核心模型 (对应 MySQL 表: tasks)
# ---------------------------------------------------------

class TaskBase(BaseModel):
    """
    任务基础字段，用于创建和更新
    """
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务详细描述")
    
    # 对应数据库新增字段
    category: str = Field(..., description="分类，如 前端、后端、设计")
    price: int = Field(..., description="赏金金额")
    duration: int = Field(..., description="截止天数")
    
    difficulty: Optional[str] = Field(None, description="难度等级")
    
    # 注意：这里定义为 List[str]，SQLModel 会自动处理 JSON 序列化
    skills: Optional[List[str]] = Field(default_factory=list, description="技能标签列表")
    
    status: Optional[int] = Field(0, description="状态：0-待审核, 1-进行中, 2-暂停, 3-完成, 4-驳回")
    taken_by: Optional[int] = Field(None, description="接单者用户ID")

class TaskCreate(TaskBase):
    """
    创建任务时的模型
    必须包含 mentor_id (发布者)
    """
    mentor_id: Optional[int] = Field(None, description="发布者ID")

class TaskUpdate(BaseModel):
    """
    更新任务时的模型 (所有字段可选)
    """
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = None
    duration: Optional[int] = None
    difficulty: Optional[str] = None
    skills: Optional[List[str]] = None
    status: Optional[int] = None
    taken_by: Optional[int] = None

class TaskOut(TaskBase):
    """
    返回给前端的完整任务模型
    """
    id: int
    mentor_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ---------------------------------------------------------
# 3. 任务交付/接单相关模型 (实战模块的核心)
# ---------------------------------------------------------

class TaskDeliveryBase(BaseModel):
    """
    用户接单/提交作业时
    """
    delivery_url: str = Field(..., description="交付物链接 (GitHub地址/演示地址)")
    comment: Optional[str] = Field(None, description="提交备注")

class TaskDeliveryCreate(TaskDeliveryBase):
    pass

class TaskDeliveryOut(TaskDeliveryBase):
    id: int
    task_id: int
    user_id: int
    submitted_at: datetime
    
    # 嵌套返回用户信息 (可选)
    # user: Optional[UserBase] = None

    class Config:
        from_attributes = True