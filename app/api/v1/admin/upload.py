import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from . import deps
from app.models import database, base  # 引入 base 模型用于记录文件元数据
from app.rag import rag_engine,vector_store        # 引入解析引擎

router = APIRouter()

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
    
@router.post("/admin/upload")
async def upload_and_process(
    file: UploadFile = File(..., description="支持 PDF, TXT, DOCX, PPTX, HTML"),
    current_user = Depends(deps.get_current_active_admin),
    db: Session = Depends(database.get_db)
):
    """
    完整版 RAG 流水线：上传 -> 解析 -> 存入向量库 -> 记录数据库
    """
    
    # 1. 校验文件类型
    allowed_extensions = {".pdf", ".txt", ".docx", ".pptx", ".html"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式")

    # 2. 保存临时文件
    file_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}{file_ext}")

    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. 执行 RAG 解析流水线 (ETL)
        chunks = rag_engine.process_file_pipeline(save_path)
        
        # ==========================================
        # 修改点 A：传递 tenant_id 给向量库
        # ==========================================
        vector_store.add_documents_to_vectorstore(chunks, tenant_id=current_user.tenant_id)

        # 4. 【核心】记录文件元数据到 SQL 数据库
        db_file = base.KnowledgeFile(
            id=file_id,
            filename=file.filename,
            file_path=save_path,
            uploader_id=str(current_user.id), # 确保类型匹配
        )
        db.add(db_file)
        db.commit()

        return {
            "message": "知识库更新成功",
            "filename": file.filename,
            "total_chunks": len(chunks),
            "vector_status": "已索引"
        }

    except Exception as e:
        db.rollback()
        # 建议：如果向量库写入成功但数据库记录失败，这里可能需要清理向量库（进阶处理）
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")