from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.base import UserDB
from app.schemas.user_schema import UserCreate, UserUpdate

# 继承通用 CRUD，指定模型和 Schema 类型
class CRUDUser(CRUDBase[UserDB, UserCreate, UserUpdate]):
    
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[UserDB]:
        """根据邮箱查询用户 (登录用)"""
        result = await db.execute(select(UserDB).where(UserDB.email == email))
        return result.scalars().first()

# 实例化，供外部直接调用
user = CRUDUser(UserDB)