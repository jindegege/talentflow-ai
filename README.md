TalentFlow-AI/
├── .env
├── main.py               # FastAPI 启动入口
├── requirements.txt
│
├── crawler/              # 爬虫模块 (OpenClaw)
│   ├── config.yaml       # OpenClaw 规则配置
│   └── pipeline.py       # 清洗与 ETL 脚本
│
├── mcp_server/           # MCP 工具服务模块
│   └── server.py         # FastMCP 定义
│
└── app/                  # 核心后端代码
    ├── __init__.py
    │
    ├── api/              # [接口层]
    │   └── v1/
    │       ├── endpoints/
    │       │   ├── auth.py
    │       │   ├── jobs.py       # 职位接口 (支持 CRUD + 语义搜索)
    │       │   └── chat.py       # AI 聊天接口
    │       └── router.py
    │
    ├── core/             # [核心层] 配置与安全
    │   ├── __init__.py
    │   ├── config.py     # 环境变量管理 (Settings)
    │   ├── security.py   # JWT, Hashing
    │   └── database.py   # MySQL & Redis 连接
    │
    ├── crud/             # [数据访问层] 传统 CRUD
    │   ├── __init__.py
    │   ├── base.py       # 通用 CRUD 类
    │   └── user.py
    │
    ├── models/           # [ORM 模型] SQLModel / SQLAlchemy
    │   ├── __init__.py
    │   └── job.py        # 职位表定义
    │
    ├── rag/              # [新增] RAG 向量检索层
    │   ├── __init__.py
    │   ├── engine.py     # 向量数据库连接 (ChromaDB/PGVector)
    │   └── service.py    # 嵌入生成与检索逻辑
    │
    ├── schemas/          # [数据校验] Pydantic
    │   ├── __init__.py
    │   └── job.py        # 职位 Pydantic 模型
    │
    └── agents/           # [新增] LangGraph AI 智能体层
        ├── __init__.py
        ├── graph.py      # 状态机定义
        └── nodes.py      # 节点逻辑
        └── states.py      # 状态逻辑


# 假设有一个名为 openclaw 的命令行工具
openclaw run crawler/config.yaml