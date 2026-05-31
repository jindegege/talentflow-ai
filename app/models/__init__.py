# app/models/__init__.py


# 先在这里定义 Base
from sqlalchemy.ext.declarative import declarative_base

# 这一步至关重要：生成 Base 对象
Base = declarative_base()