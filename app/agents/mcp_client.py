import os
import asyncio
from contextlib import AsyncExitStack
from typing import List

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.tools import load_mcp_tools

class MCPClient:
    """
    MCP 客户端管理器
    负责连接到 MCP 服务器并加载工具
    """
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.session: Optional[ClientSession] = None
        self.tools: List[BaseTool] = []

    async def connect_to_server(self, server_url: str):
        """
        连接到运行中的 MCP 服务器 (SSE 模式)
        """
        # 1. 建立 SSE 连接
        # 假设你的 mcp_server 运行在 http://127.0.0.1:8000/sse
        streams_context = sse_client(url=server_url)
        
        # 2. 进入上下文并获取读写流
        streams = await self.exit_stack.enter_async_context(streams_context)
        (read, write) = streams

        # 3. 初始化会话
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )

        # 4. 初始化握手
        await self.session.initialize()

        # 5. 加载工具 (将 MCP 工具转换为 LangChain 工具)
        self.tools = await load_mcp_tools(self.session)
        
        print(f"成功连接到 MCP 服务器: {server_url}")
        print(f"加载工具数量: {len(self.tools)}")
        for tool in self.tools:
            print(f"   - {tool.name}: {tool.description}")

    async def disconnect(self):
        await self.exit_stack.aclose()

# 全局单例 (可选，取决于你的架构)
mcp_client = MCPClient()