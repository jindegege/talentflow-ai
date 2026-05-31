import os
import sys
import json
import yaml
from app.core.database import SessionLocal
from app.models.job import Job
from app.rag.service import add_document_to_vector_db

# 模拟 OpenClaw 的 Pipeline 处理逻辑
class JobDataPipeline:
    def __init__(self, config_path="crawler/config.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        self.db = SessionLocal()

    def clean_text(self, text):
        """3.1 清洗标准化：统一格式化"""
        if not text: return ""
        # 去除HTML标签、多余空格等
        return " ".join(str(text).split())

    def process_item(self, item):
        """处理单条职位数据"""
        # 1. 数据清洗
        title = self.clean_text(item.get('title'))
        desc = self.clean_text(item.get('description'))
        
        # 2. 存入 MySQL
        job = Job(
            title=title,
            company=item.get('company'),
            location=item.get('location'),
            salary=item.get('salary'),
            description=desc,
            requirements=self.clean_text(item.get('requirements')),
            tags=json.dumps(item.get('tags', [])),
            source_url=item.get('url')
        )
        self.db.add(job)
        self.db.flush() # 获取 ID
        
        # 3. 存入向量库 (用于 3.2 人岗匹配)
        # 将职位描述和要求组合成向量文本
        vector_text = f"{title} {desc} {item.get('requirements')}"
        add_document_to_vector_db(
            doc_id=f"job_{job.id}",
            text=vector_text,
            metadata={"title": title, "company": item.get('company')}
        )
        
        self.db.commit()
        print(f"✅ 职位入库: {title}")

    def run(self):
        # 读取本地 JSON 数据（模拟爬虫抓取后的结果）
        # 实际 OpenClaw 运行后会将结果存为 JSON，这里直接读取
        data_file = self.config['job']['source']['jobs_file']
        with open(data_file, 'r', encoding='utf-8') as f:
            jobs = json.load(f)
            
        for job in jobs:
            self.process_item(job)

if __name__ == "__main__":
    # 运行命令: python crawler/pipeline.py
    pipeline = JobDataPipeline()
    pipeline.run()