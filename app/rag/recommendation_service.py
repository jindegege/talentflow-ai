from typing import List, Dict, Any, Optional
from sqlalchemy import select as sa_select
from langchain_core.documents import Document
import traceback # 用于打印详细错误堆栈
import time

# 1. 导入模型
from app.models.job_position import JobPosition
from app.models.UserProfile import UserProfile
from app.models.resume import Resume

# 2. 导入 RAG 模块
from app.rag.retriever import get_hybrid_retriever
from app.rag.reranker import global_reranker
from app.utils.logger import logger

from app.core.celery_app import celery_app

from app.models.database import SessionLocal  # 假设你有独立的数据库会话工厂

from app.rag.reranker import RerankerService


# 初始化一个不带模型权重的纯业务重排序服务
reranker_service = RerankerService()

def safe_extract_skills(data) -> List[str]:
    """提取并清洗技能列表"""
    if not data: return []
    skills = set()
    if isinstance(data, list):
        for item in data:
            if item: skills.add(str(item).strip().lower())
    elif isinstance(data, str):
        for sep in [',', '，', ';', '；', ' ']:
            if sep in data: data = data.replace(sep, ',')
        for part in data.split(','):
            clean_part = part.strip().lower()
            if clean_part: skills.add(clean_part)
    else:
        skills.add(str(data).strip().lower())
    return list(skills)

@celery_app.task(bind=True,name="app.rag.recommendation_service.generate_recommendation_task")
def generate_recommendation_task(self, user_id: int, top_k: int = 5):
    """后台异步执行的重度推荐任务"""
    db = SessionLocal() # 为当前任务创建独立的数据库会话
    start_time = time.time()
    
    try:
        logger.info(f"[Celery Worker] 开始为用户 {user_id} 异步生成推荐...")

        # 1. 获取用户基础信息
        user_profile = db.execute(sa_select(UserProfile).where(UserProfile.user_id == user_id)).scalars().first()
        if not user_profile:
            return {"status": "failed", "error": "用户不存在"}

        # 获取默认简历
        resume = db.execute(sa_select(Resume).where(Resume.user_id == user_id, Resume.is_default == 1)).scalars().first()

        # 2. 构建查询文本
        query_parts = []
        source_data = resume if resume else user_profile
        user_skills_list = safe_extract_skills(source_data.skills)
        if user_skills_list: query_parts.extend(user_skills_list)
        
        if isinstance(source_data, UserProfile) and source_data.expected_position:
            query_parts.append(f"目标职位：{source_data.expected_position}")
        if resume and resume.summary:
            query_parts.append(f"个人总结：{resume.summary}")
            
        final_query = " ".join(filter(None, query_parts))
        if not final_query.strip():
            return {"status": "failed", "error": "用户画像信息不足，无法生成推荐"}

        # 3. RAG 检索与重排序 (纯 CPU 下的繁重计算)
        retriever = get_hybrid_retriever(k=top_k * 3)
        retrieved_docs: List[Document] = retriever.invoke(final_query)
        logger.info(f"向量检索完成，召回 {len(retrieved_docs)} 条")

        # 调用重排序（限制最大精排数量为 10，防止 CPU 卡死）
        ranked_docs = reranker_service.rank(final_query, retrieved_docs, top_k=top_k * 2, max_rerank_limit=10)
        logger.info(f"重排序完成")

        if not ranked_docs:
            return {"status": "success", "data": []}

        # 4. 数据库映射与打分
        doc_job_ids = [doc.metadata.get("job_id") for doc in ranked_docs if doc.metadata.get("job_id")]
        jobs_map = {job.job_id: job for job in db.execute(sa_select(JobPosition).where(JobPosition.job_id.in_(doc_job_ids))).scalars().all()}

        recommendations = []
        user_skills_set = set(user_skills_list)

        for doc in ranked_docs:
            job_obj = jobs_map.get(doc.metadata.get("job_id"))
            if not job_obj: continue

            job_skills_set = set(safe_extract_skills(job_obj.required_skills))
            matched_skills = user_skills_set.intersection(job_skills_set)
            skill_match_rate = len(matched_skills) / len(job_skills_set) if job_skills_set else 0
            
            rag_score = doc.metadata.get("relevance_score", doc.metadata.get("score", 0.5))
            final_score = (rag_score * 0.7 + skill_match_rate * 0.3) * 100

            recommendations.append({
                "job_id": job_obj.job_id,
                "job_title": job_obj.title,
                "company": job_obj.company,
                "salary": job_obj.salary,
                "score": round(final_score, 1),
                "matched_skills": list(matched_skills),
                "reason": f"匹配度 {int(skill_match_rate * 100)}%"
            })

        recommendations.sort(key=lambda x: x["score"], reverse=True)
        result_data = recommendations[:top_k]
        
        logger.info(f"用户 {user_id} 推荐生成完毕，总耗时 {time.time() - start_time:.2f}s")
        return {"status": "success", "data": result_data}

    except Exception as e:
        logger.error(f"推荐任务执行失败: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()

class RecommendationService:
    def __init__(self, db_session):
        self.db = db_session

    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """获取用户画像"""
        try:
            stmt = sa_select(UserProfile).where(UserProfile.user_id == user_id)
            result = self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            logger.error(f"获取用户画像失败: {e}")
            return None

    def _safe_extract_skills(self, data) -> List[str]:
        """
        安全提取技能列表的辅助函数
        处理 List, String, None 等各种情况
        """
        if not data:
            return []

        # 情况 A: 已经是列表 (最常见)
        if isinstance(data, list):
            # 过滤掉非字符串元素
            return [str(item).strip() for item in data if item]

        # 情况 B: 是字符串 (可能是 "Python,Java" 或 "Python")
        if isinstance(data, str):
            if ',' in data:
                return [item.strip() for item in data.split(',') if item.strip()]
            else:
                return [data.strip()] if data.strip() else []

        # 情况 C: 其他未知类型 (强制转字符串)
        logger.warning(f"发现非标准技能数据格式: {type(data)}, 内容: {data}")
        return [str(data)]

    def recommend_jobs(self, user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        推荐主流程：基于简历详情 + 用户画像构建查询
        """
        start_time = time.time()
        logger.info(f"--- 开始推荐任务 (User: {user_id}) ---")
        try:
            # 1. 获取用户基础信息
            user_profile = self.get_user_profile(user_id)
            if not user_profile:
                logger.error(f"用户 {user_id} 不存在或无画像")
                return []

            logger.info(f"开始为用户 {user_id} 生成推荐...")

            # 2. 获取默认简历
            resume = None
            try:
                resume_stmt = sa_select(Resume).where(
                    Resume.user_id == user_id,
                    Resume.is_default == 1
                )
                resume_result = self.db.execute(resume_stmt)
                resume = resume_result.scalars().first()

                if resume:
                    logger.debug(f"找到默认简历 ID: {resume.id}")
                else:
                    logger.info(f"用户 {user_id} 无默认简历，将回退使用画像数据")

            except Exception as e:
                logger.error(f"查询简历失败: {e}")

            # --- 构建查询向量 ---
            query_parts = []
            skills: List[str] = []

            # 3. 提取技能 (优先简历，其次画像)
            if resume and resume.skills:
                skills = self._safe_extract_skills(resume.skills)
                logger.debug(f"从简历提取技能: {skills}")
            elif user_profile and user_profile.skills:
                skills = self._safe_extract_skills(user_profile.skills)
                logger.debug(f"从画像提取技能: {skills}")

            # 安全 extend
            if skills:
                query_parts.extend(skills)

            # 4. 提取文本经历 (优先简历)
            def safe_append(text: Any, max_len: int = 200):
                if not text:
                    return
                text_str = str(text)
                if text_str.strip():
                    query_parts.append(text_str[:max_len])

            if resume:
                safe_append(resume.summary)
                safe_append(resume.work_experience)
                safe_append(resume.project_experience)
            else:
                # 无简历时使用画像
                if user_profile.profile_summary:
                    query_parts.append(str(user_profile.profile_summary))

            # 5. 意向职位
            if user_profile.expected_position:
                query_parts.append(str(user_profile.expected_position))

            # 组合查询字符串
            final_query = " ".join(filter(None, query_parts))
            logger.info(f"构建检索查询文本 (长度: {len(final_query)}): {final_query[:100]}...")

            if not final_query.strip():
                logger.warning("构建的查询文本为空，无法进行推荐")
                return []

            # --- RAG 检索流程 ---
            try:
                t1 = time.time() 
                retriever = get_hybrid_retriever(k=top_k * 3)
                retrieved_docs: List[Document] = retriever.invoke(final_query)
                logger.info(f"向量检索耗时: {time.time() - t1:.2f}秒, 找到 {len(retrieved_docs)} 条")
                logger.info(f"检索到 {len(retrieved_docs)} 个文档片段")

                if not retrieved_docs:
                    return []

                # 重排序
                t2 = time.time()
                ranked_docs = global_reranker.rank(final_query, retrieved_docs, top_k=5)
                logger.info(f"重排序耗时: {time.time() - t2:.2f}秒")
                # --- 结果处理 ---
                recommendations = []

                # 批量获取职位信息
                doc_job_ids = [
                    doc.metadata.get("job_id")
                    for doc in ranked_docs
                    if doc.metadata.get("job_id")
                ]

                if not doc_job_ids:
                    return []

                jobs_stmt = sa_select(JobPosition).where(JobPosition.job_id.in_(doc_job_ids))
                jobs_result = self.db.execute(jobs_stmt)
                jobs_map = {job.job_id: job for job in jobs_result.scalars().all()}

                # 计算技能匹配
                user_skills_set = set([s.lower() for s in skills])

                for doc in ranked_docs:
                    job_id = doc.metadata.get("job_id")
                    if job_id in jobs_map:
                        job_obj = jobs_map[job_id]

                        # 解析职位技能要求
                        job_skills_raw = job_obj.required_skills or []
                        job_skills_list = self._safe_extract_skills(job_skills_raw)
                        job_skills_set = set([s.lower() for s in job_skills_list])

                        # 计算分数
                        matched_skills = user_skills_set.intersection(job_skills_set)
                        skill_score = (
                            len(matched_skills) / len(job_skills_set)
                            if job_skills_set
                            else 0
                        )

                        rag_score = doc.metadata.get(
                            "relevance_score", doc.metadata.get("score", 0.5)
                        )

                        final_score = (rag_score * 0.7 + skill_score * 0.3) * 100

                        recommendations.append(
                            {
                                "job": job_obj,
                                "score": round(final_score, 1),
                                "matched_skills": list(matched_skills),
                                "reason": f"技能匹配度 {int(skill_score * 100)}%",
                            }
                        )

                # 排序并返回
                recommendations.sort(key=lambda x: x["score"], reverse=True)
                result = recommendations[:top_k]
                logger.info(f"生成推荐完成，共 {len(result)} 条")
                return result

            except Exception as rag_err:
                logger.error(f"RAG 检索或处理过程出错: {rag_err}")
                logger.error(traceback.format_exc()) # 打印详细堆栈
                return []

        except Exception as e:
            logger.error(f"推荐服务整体异常: {e}")
            logger.error(traceback.format_exc())
            return []