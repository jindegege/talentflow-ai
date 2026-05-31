from typing import Any, Dict, List, Optional
from langchain_core.callbacks import AsyncCallbackHandler
import asyncio

class AsyncCallbackHandler(AsyncCallbackHandler):
    """
    自定义异步回调处理器，用于实现 LLM 的流式输出
    """
    def __init__(self):
        # 使用 asyncio.Queue 在线程/协程间传递 token
        self.queue = asyncio.Queue()
        self.done = asyncio.Event() # 用于标记生成结束

    async def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any
    ) -> None:
        """LLM 开始运行时调用。
        这里可以用来重置状态或清空队列，防止上一次残留数据影响。
        """
        # 重置队列，防止旧数据干扰（虽然每次请求通常是新实例，但为了保险）
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except asyncio.QueueEmpty:
                break
        self.done.clear()

    async def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        """Chain 开始时调用，同样做清理工作"""
        await self.on_llm_start(serialized, [], **kwargs)

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """
        当 LLM 生成新 Token 时触发
        """
        if token:
            # 将 token 放入队列
            await self.queue.put(token)

    async def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """
        当 LLM 生成结束时触发
        """
        # 放入结束标记 (None)
        await self.queue.put(None)
        self.done.set()

    async def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        """
        当 LLM 发生错误时触发
        """
        # 放入结束标记，防止前端一直等待
        await self.queue.put(None)
        self.done.set()

            
    async def aiter(self):
        while True:
            try:
                # 设置超时，防止 queue.get() 永久阻塞
                token = await asyncio.wait_for(self.queue.get(), timeout=30.0)
                if token is None:
                    break
                yield token
            except asyncio.TimeoutError:
                # 超时处理，防止死锁
                break