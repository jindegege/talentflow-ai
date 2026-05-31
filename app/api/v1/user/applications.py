from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import logging

# 请根据你的实际项目路径调整以下导入
from app.models.database import get_db 
from app.core.deps import get_current_user
from app.models.user import User
from app.models.application import Application
from app.models.job_position import JobPosition
from pydantic import BaseModel # 引入Pydantic用于请求体校验

from dotenv import load_dotenv
load_dotenv()  # 自动加载 .env

router = APIRouter(prefix="/api/v1/user", tags=["投递记录"])
logger = logging.getLogger("api.applications")


from langsmith import traceable



# ==========================================
# 1. Pydantic 响应与请求模型定义
# ==========================================

class ApplicationOut(BaseModel):
    """单条投递记录响应模型"""
    id: int
    job_id: str
    status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    
    class Config:
        from_attributes = True

class ApplicationListResponse(BaseModel):
    """投递记录列表包装模型"""
    total: int
    items: List[ApplicationOut]

class UpdateStatusRequest(BaseModel):
    """更新状态的请求体模型"""
    status: str  # 例如: "interview_confirmed"

# ==========================================
# 2. API 接口实现
# ==========================================

@router.get("/applications/my", response_model=ApplicationListResponse)
@traceable(run_type="chain", name="get_my_applications_api_call")
def get_my_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # 筛选参数
    status: Optional[str] = Query(None, description="投递状态"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    # 分页参数
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=100)
):
    """
    获取我的投递记录列表（支持分页、按状态/时间筛选）
    """
    logger.info(f"查询用户 {current_user.id} 的投递记录，筛选: {status}, {start_date} 至 {end_date}")

    try:
        # 1. 构建基础查询 (左连接 jobs 表以获取职位信息)
        query = db.query(Application, JobPosition.title, JobPosition.company)\
                  .outerjoin(JobPosition, Application.job_id == JobPosition.id)\
                  .filter(Application.user_id == current_user.id)
        
        # 2. 应用筛选条件
        if status:
            query = query.filter(Application.status == status)
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(Application.created_at >= start_dt)
            except ValueError:
                pass 

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                query = query.filter(Application.created_at <= end_dt)
            except ValueError:
                pass

        # 3. 获取总数 (用于分页)
        total = query.count()

        # 4. 执行查询并分页
        results = query.order_by(Application.created_at.desc())\
                       .offset(skip)\
                       .limit(limit)\
                       .all()

        # 5. 格式化数据
        items = []
        for app_row, job_title, company in results:
            items.append(ApplicationOut(
                id=app_row.id,
                job_id=app_row.job_id,
                status=app_row.status,
                created_at=app_row.created_at,
                updated_at=app_row.updated_at,
                job_title=job_title,
                company=company
            ))

        return ApplicationListResponse(total=total, items=items)

    except Exception as e:
        logger.error(f"查询投递记录失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.get("/applications/{application_id}", response_model=ApplicationOut)
def get_application_detail(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取某一条投递记录的详细信息（点击“查看详情/反馈”时调用）
    """
    try:
        # 查询该用户的特定投递记录，并关联职位信息
        result = db.query(Application, JobPosition.title, JobPosition.company)\
                   .outerjoin(JobPosition, Application.job_id == JobPosition.id)\
                   .filter(Application.id == application_id, Application.user_id == current_user.id)\
                   .first()
        
        if not result:
            raise HTTPException(status_code=404, detail="投递记录不存在或无权访问")

        app_row, job_title, company = result
        
        return ApplicationOut(
            id=app_row.id,
            job_id=app_row.job_id,
            status=app_row.status,
            created_at=app_row.created_at,
            updated_at=app_row.updated_at,
            job_title=job_title,
            company=company
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询投递详情失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")


@router.patch("/applications/{application_id}/status", response_model=ApplicationOut)
def update_application_status(
    application_id: int,
    request: UpdateStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新投递记录的状态（用于前端“确认面试”等操作）
    """
    try:
        # 1. 查找记录并确保属于当前用户
        application = db.query(Application).filter(
            Application.id == application_id, 
            Application.user_id == current_user.id
        ).first()

        if not application:
            raise HTTPException(status_code=404, detail="投递记录不存在或无权修改")

        # 2. 更新状态 (例如将 status 更新为 'interview_confirmed')
        application.status = request.status
        application.updated_at = datetime.utcnow() # 更新更新时间
        db.commit()
        db.refresh(application)

        # 3. 重新查询关联信息并返回最新的数据
        result = db.query(Application, JobPosition.title, JobPosition.company)\
                   .outerjoin(JobPosition, Application.job_id == JobPosition.id)\
                   .filter(Application.id == application.id)\
                   .first()
        
        app_row, job_title, company = result
        return ApplicationOut(
            id=app_row.id,
            job_id=app_row.job_id,
            status=app_row.status,
            created_at=app_row.created_at,
            updated_at=app_row.updated_at,
            job_title=job_title,
            company=company
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新投递状态失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="服务器内部错误")