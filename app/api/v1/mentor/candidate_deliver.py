from fastapi import APIRouter, Depends, Query,HTTPException
from typing import List, Optional
from sqlmodel import select,func

# 假设你的路径别名如下，请根据实际项目调整
from app.models.database import Session, get_db
from app.models.resume import Resume
from app.models.base import UserDB
from app.models.job_position import JobPosition
from app.schemas.resume_schema import ResumeApplicationOut

from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/hr", tags=["HR-投递管理"])

@router.get("/applications", response_model=List[ResumeApplicationOut])
def get_resume_applications(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db)
):
    """
    获取人才投递管理列表
    逻辑：查询 Resume 表，同时关联 User 表拿名字，关联 JobPosition 表拿职位名
    """
    
    # 1. 构建查询语句
    # 我们选择 Resume 表的主要字段，以及关联表的特定字段
    statement = (
        select(
            Resume.id,
            # 优先取简历表里的名字，如果没有则取用户表的 full_name
            # 这里使用 func.coalesce 类似于 SQL 的 IFNULL
            func.coalesce(Resume.name, UserDB.full_name).label("candidate_name"),
            JobPosition.title.label("job_title"),
            Resume.skills.label("job_skills"),
            Resume.created_at.label("applied_at"),
            Resume.status
        )
        # 2. 关联 User 表 (users)
        # Resume.user_id == UserDB.id
        .join(UserDB, Resume.user_id == UserDB.id)
        # 3. 关联 JobPosition 表 (job_positions)
        # Resume.target_job_id == JobPosition.id
        .join(JobPosition, Resume.target_job_id == JobPosition.job_id)
        # 4. 排序（最新的投递在最前面）
        .order_by(Resume.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    # 5. 执行查询
    results = db.execute(statement).all()
    
    # 6. 格式化返回数据
    # results 是元组列表，我们需要把它转成字典或模型
    response_data = []
    for row in results:
        response_data.append({
            "id": row.id,
            "candidate_name": row.candidate_name,
            "job_title": row.job_title,
            # 如果是 JSON 字段，可能需要转成字符串，视前端需求而定
            "job_skills": row.job_skills if isinstance(row.job_skills, str) else ",".join(row.job_skills) if row.job_skills else "",
            "applied_at": row.applied_at,
            "status": row.status
        })
        
    return response_data


# 定义处理投递的请求体
class ProcessResumeRequest(BaseModel):
    status: str
    remark: Optional[str] = ""

# 1. 获取简历投递详情
@router.get("/applications/{app_id}")
def get_application_detail(app_id: int, db: Session = Depends(get_db)):
    """
    获取单条投递的完整简历详情
    """
    statement = (
        select(
            Resume.id,
            Resume.user_id,
            Resume.target_job_id,
            Resume.skills,
            Resume.status,
            Resume.created_at,
            Resume.source,  # 假设你的 Resume 模型里有简历附件链接字段
            Resume.remark,
            UserDB.full_name,
            JobPosition.title.label("job_title")
        )
        .join(UserDB, Resume.user_id == UserDB.id)
        .join(JobPosition, Resume.target_job_id == JobPosition.job_id)
        .where(Resume.id == app_id)
    )
    
    # 保持原有风格：使用 execute().first() 获取单条元组数据
    result = db.execute(statement).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="投递记录不存在")
        
    # 将元组数据转为字典返回，保持与之前接口返回格式一致
    return {
        "id": result.id,
        "candidate_name": result.full_name,
        "job_title": result.job_title,
        "job_skills": result.skills if isinstance(result.skills, str) else ",".join(result.skills) if result.skills else "",
        "applied_at": result.created_at,
        "status": result.status,
        "source": result.source,
        "remark": result.remark
    }

# 2. 处理投递（更新状态）
@router.patch("/applications/{app_id}/process")
def process_application(
    app_id: int, 
    request: ProcessResumeRequest, 
    db: Session = Depends(get_db)
):
    """
    更新投递状态和备注
    """
    # 先通过主键获取对象实例，方便直接修改属性
    statement = select(Resume).where(Resume.id == app_id)
    # 保持原有风格：使用 execute().scalar_one_or_none() 获取模型对象
    resume = db.execute(statement).scalar_one_or_none()
    
    if not resume:
        raise HTTPException(status_code=404, detail="投递记录不存在")

    # 更新状态和备注
    resume.status = request.status
    # 假设你的 Resume 模型里有 remark 字段用来存处理意见
    if hasattr(resume, 'remark'):
        resume.remark = request.remark
        
    db.add(resume)
    db.commit()
    db.refresh(resume)
    
    return {"message": "处理成功", "status": resume.status}