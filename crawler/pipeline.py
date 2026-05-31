import os
import sys
import json
import time
from typing import List, Dict

# 添加项目根目录到系统路径，以便导入 app 模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from app.core.database import SessionLocal, engine
from app.models.job import Job, Resume # 假设你已经在 models 中定义了这两个表
from app.rag.service import RAGService # 向量服务

class LocalDataPipeline:
    def __init__(self, config_path="config.yaml"):
        self.config = self.load_config(config_path)
        self.db = SessionLocal()
        self.rag_service = RAGService()
        
    def load_config(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load_json(self, filepath):
        """读取本地 JSON 文件"""
        print(f"正在读取数据源: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def clean_text(self, text):
        """简单的清洗逻辑：去空格、换行"""
        if not text:
            return ""
        return " ".join(str(text).split())

    def import_jobs(self):
        """导入职位数据到 MySQL 和 VectorDB"""
        source_file = self.config['job']['source']['jobs_file']
        raw_data = self.load_json(source_file)
        
        print(f"开始导入 {len(raw_data)} 条职位数据...")
        
        for item in raw_data:
            # 1. 数据清洗
            description = self.clean_text(item.get('description'))
            requirements = self.clean_text(item.get('requirements'))
            
            # 合并文本用于向量化
            content_for_vector = f"{item.get('title')} {description} {requirements}"
            
            # 2. 写入 MySQL (结构化存储)
            db_job = Job(
                external_id=item.get('id'), # 原始ID
                title=item.get('title'),
                company=item.get('company'),
                location=item.get('location'),
                salary=item.get('salary'),
                description=description,
                requirements=requirements,
                tags=json.dumps(item.get('tags', [])) # 存为 JSON 字符串
            )
            self.db.add(db_job)
            self.db.flush() # 刷新以获取生成的 ID
            
            # 3. 写入 VectorDB (语义存储)
            # 注意：这里使用数据库生成的 ID 作为向量库的元数据
            self.rag_service.add_document(
                doc_id=f"job_{db_job.id}",
                text=content_for_vector,
                metadata={
                    "type": "job",
                    "title": item.get('title'),
                    "job_id": db_job.id
                }
            )
            
        self.db.commit()
        print("职位数据导入完成！")

    def import_resumes(self):
        """导入简历数据"""
        source_file = self.config['job']['source']['resumes_file']
        raw_data = self.load_json(source_file)
        
        print(f"开始导入 {len(raw_data)} 份简历数据...")
        
        for item in raw_data:
            summary = self.clean_text(item.get('summary'))
            skills = ", ".join(item.get('skills', []))
            
            content_for_vector = f"{item.get('name')} {skills} {summary}"
            
            # 写入 MySQL
            db_resume = Resume(
                external_id=item.get('id'),
                name=item.get('name'),
                experience=item.get('experience'),
                skills=skills,
                summary=summary
            )
            self.db.add(db_resume)
            self.db.flush()
            
            # 写入 VectorDB
            self.rag_service.add_document(
                doc_id=f"resume_{db_resume.id}",
                text=content_for_vector,
                metadata={
                    "type": "resume",
                    "name": item.get('name'),
                    "resume_id": db_resume.id
                }
            )
            
        self.db.commit()
        print("简历数据导入完成！")

    def run(self):
        """执行整个管道"""
        try:
            self.import_jobs()
            self.import_resumes()
        finally:
            self.db.close()

if __name__ == "__main__":
    # 运行命令: python crawler/pipeline.py
    pipeline = LocalDataPipeline()
    pipeline.run()