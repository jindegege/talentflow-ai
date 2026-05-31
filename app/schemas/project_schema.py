from pydantic import BaseModel,Field
from typing import Optional
from datetime import datetime

# ==========================================
# 输入模型 (Input Schemas)
# ==========================================

class ProjectCreate(BaseModel):
    """
    发布项目时的请求体 (POST /projects)
    """
    title: str
    category: str
    # 修改 1: 允许输入字符串，例如 "1000元" 或 "面议"
    level: str
    reward: Optional[str] = None 
    tags: str
    is_active: bool
    description: Optional[str] = None

# ==========================================
# 输出模型 (Output Schemas / Response)
# ==========================================

from pydantic import BaseModel, Field
from typing import Optional, List, Union

class ProjectRead(BaseModel):
    id: int
    title: str = Field(..., min_length=1, description="项目标题")
    category: str = Field(..., description="分类")
    level: str = Field(..., description="难度等级")
    
    # 修正 1: 允许字符串或数字，防止前端传空字符串报错
    reward: Optional[Union[str, float, int]] = None 
    
    # 修正 2: 明确接收字符串 (前端传 "a,b,c")
    # 如果你希望后端自动把它转成列表，需要在逻辑里处理，但模型定义先接收 str
    tags: str = "" 
    
    description: Optional[str] = ""
    
    # 修正 3: 允许 0/1 或 true/false
    is_active: Union[int, bool] = 1 

class ProjectOut(ProjectRead):
    """
    API 响应模型
    """
    pass