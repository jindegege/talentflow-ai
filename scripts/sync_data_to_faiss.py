import sys
import os
import numpy as np  # 引入 numpy 用于计算模长

# 关键：将项目根目录添加到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session
from sqlalchemy import select as sa_select

from app.models.database import engine 

from app.models.job_position import JobPosition
# 引入 FAISS 版的向量库函数
from app.rag.vector_store import get_vectorstore, add_documents_to_vectorstore
from app.utils.logger import logger

def sync_jobs_to_vectorstore():
    """
    将 MySQL 中的职位数据同步到 FAISS 向量库
    """
    logger.info("开始同步职位数据到 FAISS...")
    
    # 1. 获取向量库连接与 Embedding 模型
    try:
        vectorstore_dict = get_vectorstore()
        embedding_func = vectorstore_dict["embedding_function"]
        
        # 调试：检查维度
        test_embedding = embedding_func.embed_query("test")
        actual_dim = len(test_embedding)
        logger.info(f"同步脚本实际加载的模型维度: {actual_dim}")
        
        if actual_dim != 512: 
            logger.error(f"检测到维度错误！期望 512，实际得到 {actual_dim}。请检查模型路径。")
            return
            
    except Exception as e:
        logger.error(f"初始化向量库失败: {e}")
        return

    # 2. 获取 SQL 数据库会话并查询
    try:
        with Session(engine) as session:
            stmt = sa_select(JobPosition)
            result = session.execute(stmt)
            jobs = result.scalars().all()
            
            logger.info(f"从 MySQL 中读取到 {len(jobs)} 个有效职位")

            if not jobs:
                logger.warning("没有职位需要同步")
                return

            # 3. 准备数据用于 FAISS 写入
            documents = []
            metadatas = []
            valid_count = 0
            skipped_count = 0
            
            for job in jobs:
                # 兼容字段名
                company_val = getattr(job, 'company', '') or getattr(job, 'company_name', '')
                
                # 构建向量化文本
                content_text = f"{job.title} {company_val} {job.description}"
                
                # 过滤空内容
                if not content_text.strip():
                    logger.warning(f"职位 {job.id} 内容为空，跳过。")
                    skipped_count += 1
                    continue

                # --- 【核心修复】：在此处生成向量并检查模长 ---
                try:
                    embedding = embedding_func.embed_query(content_text)
                    
                    # 计算 L2 范数 (模长)
                    norm = np.linalg.norm(embedding)
                    
                    # 如果模长极小（接近0），说明是无效向量，存入 FAISS 会导致除零错误
                    if norm < 1e-9:
                        logger.error(f"职位 {job.id} ({job.title}) 生成了零向量！已跳过。")
                        skipped_count += 1
                        continue
                        
                    valid_count += 1
                    
                except Exception as e:
                    logger.error(f"职位 {job.id} 向量化失败: {e}")
                    skipped_count += 1
                    continue
                # --------------------------------------------

                # 过滤 None 值
                safe_skills = job.required_skills if job.required_skills else []
                safe_salary = job.salary if job.salary else "面议"
                
                # 在构建 metadata 字典时
                metadata = {
                    # 修改点：这里改为 job.job_id，即 'JOB-001' 格式
                    "job_id": job.job_id, 
                    "title": job.title,
                    "company": company_val,
                    "salary": safe_salary,
                    "skills": safe_skills,
                    "source": "mysql_sync",
                    "content": content_text 
                }

                documents.append(content_text)
                metadatas.append(metadata)

            # 4. 写入 FAISS (如果存在有效数据)
            if valid_count > 0:
                add_documents_to_vectorstore(documents, metadatas)
                logger.info(f"成功同步 {valid_count} 个职位到 FAISS")
            else:
                logger.warning("没有有效数据写入 FAISS，可能是所有数据都被过滤了。")
                
            if skipped_count > 0:
                logger.warning(f"共有 {skipped_count} 条数据因内容无效或向量化错误被跳过。")

    except Exception as e:
        logger.error(f"数据库读取或写入失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    sync_jobs_to_vectorstore()