# 文件路径：app/api/v1/chat.py
# 作用：聊天相关的 HTTP 接口
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Form,Response
from sqlalchemy.orm import Session
from sqlalchemy import select

# 1. 导入依赖和模型
from . import deps
from app.models import database, base
from app import schemas,crud

import asyncio

from app.rag import vector_store   # 引入解析引擎

from app.rag.chain import get_rag_chain

# 导入刚才写的重排序器
from app.rag.reranker import global_reranker
# 导入之前的混合检索器
from app.rag.retriever import get_hybrid_retriever

from app.utils.logger import logger

router = APIRouter()

@router.get("/chat/sessions", response_model=List[schemas.ChatSessionResponse])
def get_history_sessions(
    current_user: base.UserDB = Depends(deps.get_current_user), 
    db: Session = Depends(database.get_db)
):
    sessions = db.query(base.ChatSessionDB).filter(
        base.ChatSessionDB.user_id == current_user.id
    ).order_by(base.ChatSessionDB.created_at.desc()).all()
    
    return sessions

@router.delete("/chat/sessions/{session_id}", status_code=200)
def api_delete_session(
    session_id: int, 
    current_user: base.UserDB = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    
    """
    删除会话
    """
    # 1. 先查询会话，必须带上 user_id 过滤
    session = db.execute(
        select(base.ChatSessionDB)
        .where(base.ChatSessionDB.id == session_id, base.ChatSessionDB.user_id == current_user.id)
    ).scalar_one_or_none()
    
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="无权操作")
        
    db.delete(session)
    db.query(base.ChatMessageDB).filter(base.ChatMessageDB.session_id == session_id).delete()
    db.commit()
    
    return {"detail": "删除成功"}

# 2. 获取右侧：特定会话的详细消息
@router.get("/chat/sessions/{session_id}/messages", response_model=List[schemas.ChatMessageResponse])
async def get_session_messages(
    session_id: int,
    user=Depends(deps.get_current_user),
    db=Depends(database.get_db)
):
    """
    获取指定会话 ID 的所有消息记录（用于右侧聊天窗口）
    """
    # 1. 验证会话是否属于该用户
    session = crud.get_session_by_id(db, session_id=session_id, user_id=user.id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或无权限")
    
    # 2. 获取该会话下的所有消息
    messages = crud.get_messages_by_session(db, session_id=session_id)
    return messages

# 聊天路由 ---
# @router.post("/chat")
# def chat(
#     message: str = Form(...),
#     session_id: Optional[int] = Form(None),
#     current_user: base.UserDB = Depends(deps.get_current_user),
#     db: Session = Depends(database.get_db)
# ):
#     """
#     聊天接口（纯消费模式）：
#     1. 用户输入问题
#     2. 系统基于租户已有的向量库进行检索回答
#     """
    
#     # 1. 处理会话 (Session) 逻辑
#     if not session_id:
#         # 如果是新对话，创建会话记录
#         new_session = base.ChatSessionDB(
#             user_id=current_user.id,
#             title=message[:20] # 简单截取前20字作为标题
#         )
#         db.add(new_session)
#         db.commit()
#         db.refresh(new_session)
#         session_id = new_session.id
#     else:
#         # 如果是旧对话，校验权限
#         existing_session = db.get(base.ChatSessionDB, session_id)
#         if not existing_session:
#             raise HTTPException(status_code=403, detail="无权访问此会话或会话不存在")

#     # 2. 保存用户输入的消息
#     user_msg = base.ChatMessageDB(
#         session_id=session_id, 
#         role="user", 
#         content=message
#     )
#     db.add(user_msg)
#     db.commit()

#     # 3. RAG 核心逻辑：检索 + 生成
#     try:
#         # A. 获取该租户专属的向量数据库实例
#         # 注意：这里不再涉及文件上传，而是直接连接已存在的库
#         vectorstore = vector_store.get_vectorstore()
        
#         # B. 构建检索链
#         rag_chain = get_rag_chain(vectorstore)
        
#         # C. 调用模型 (假设 invoke 接收字符串返回字符串)
#         # 如果需要流式输出，这里需要改为 StreamingResponse 逻辑
#         response_content = rag_chain.invoke(message)
        
#         # 处理可能的返回格式 (dict vs string)
#         if isinstance(response_content, dict):
#             response_text = response_content.get("answer", str(response_content))
#         else:
#             response_text = str(response_content)
            
#     except Exception as e:
#         # 生产环境建议记录日志而不是直接返回错误详情
#         response_text = f"抱歉，系统在处理您的请求时遇到错误: {str(e)}"
#         print(f"RAG Error: {e}")

#     # 4. 保存 AI 的回答
#     ai_msg = base.ChatMessageDB(
#         session_id=session_id, 
#         role="assistant", 
#         content=response_text
#     )
#     db.add(ai_msg)
#     db.commit()

#     return {
#         "session_id": session_id,
#         "response": response_text
#     }




# --- 自定义一个强制刷新的 Response 类 ---
# class NoBufferStreamingResponse(Response):
#     media_type = "text/event-stream"
    
#     def __init__(self, content, status_code=200, headers=None, media_type=None, background=None):
#         self.body_iterator = content
#         self.status_code = status_code
#         if media_type is not None:
#             self.media_type = media_type
#         self.background = background
#         self.init_headers(headers)

#     async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
#         # 1. 发送响应头
#         await send({
#             "type": "http.response.start",
#             "status": self.status_code,
#             "headers": self.raw_headers,
#         })
        
#         # 2. 循环发送数据体
#         async for chunk in self.body_iterator:
#             if isinstance(chunk, str):
#                 chunk = chunk.encode("utf-8")
            
#             # 这里的 send 是 ASGI 协议的 send 函数
#             # 我们直接喂给它数据，不进行任何缓冲
#             await send({
#                 "type": "http.response.body",
#                 "body": chunk,
#                 "more_body": True, # 告诉浏览器：别急，还有后续
#             })
            
#             # 强制让出控制权，防止事件循环阻塞
#             await asyncio.sleep(0)

#         # 3. 发送结束信号
#         await send({"type": "http.response.body", "body": b"", "more_body": False})
        
#         if self.background:
#             await self.background()

# # --- 路由代码 ---
# @router.post("/chat")
# async def chat_endpoint(
#     message: str = Form(...),
#     session_id: Optional[int] = Form(None),
#     current_user: base.UserDB = Depends(deps.get_current_user),
#     db: Session = Depends(database.get_db)
# ):
    
#         # 1. 处理会话 (Session) 逻辑
#     if not session_id:
#         # 如果是新对话，创建会话记录
#         new_session = base.ChatSessionDB(
#             user_id=current_user.id,
#             title=message[:20] # 简单截取前20字作为标题
#         )
#         db.add(new_session)
#         db.commit()
#         db.refresh(new_session)
#         session_id = new_session.id
#     else:
#         # 如果是旧对话，校验权限
#         existing_session = db.get(base.ChatSessionDB, session_id)
#         if not existing_session:
#             raise HTTPException(status_code=403, detail="无权访问此会话或会话不存在")

#     # 2. 保存用户输入的消息
#     user_msg = base.ChatMessageDB(
#         session_id=session_id, 
#         role="user", 
#         content=message
#     )
#     db.add(user_msg)
#     db.commit()
    
#     try:
#         vectorstore = vector_store.get_vectorstore()
#         chain = get_rag_chain(vectorstore)
        
#         async def event_generator():
#             full_response_text = "" # 【关键】用于在内存中累积完整的回答
#             try:
#                 async for event in chain.astream_events({"input": message}, version="v1"):
#                     if event['event'] == 'on_chat_model_stream':
#                         content = event['data']['chunk'].content
#                         if content:
#                             full_response_text += content
#                             # 这里不要加 padding 了，用自定义类直接发
#                             yield f"data: {content}\n\n"
                            
#                 yield "data: [DONE]\n\n"
#             except Exception as e:
#                 print(e)
         
#         # 4. 保存 AI 的回答
#         # --- D.流式传输结束后，将完整内容存入数据库 ---
#             # 我们不在循环里存，因为数据库写入很慢，会卡住打字效果。
#             # 等字都发完了，再一次性写入数据库。
#             if full_response_text:
#                 try:
#                     ai_msg = base.ChatMessageDB(
#                         session_id=session_id, 
#                         role="assistant", 
#                         content=full_response_text
#                     )
#                     db.add(ai_msg)
#                     db.commit()
#                     print(f"消息已入库: {full_response_text[:20]}...")
#                 except Exception as e:
#                     print(f"入库失败: {e}")
#                     db.rollback()
     
#         # 使用我们自定义的 NoBufferStreamingResponse
#         return NoBufferStreamingResponse(
#             event_generator(),
#             media_type="text/event-stream;charset=utf-8",
#             headers={
#                 "Cache-Control": "no-cache",
#                 "Connection": "keep-alive",
#                 "X-Accel-Buffering": "no",
#                 "Transfer-Encoding": "chunked" # 显式声明分块传输
#             }
#         )

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))




# --- 1. 自定义无缓冲 Response 类 (保持你的代码) ---
class NoBufferStreamingResponse(Response):
    media_type = "text/event-stream"
    
    def __init__(self, content, status_code=200, headers=None, media_type=None, background=None):
        self.body_iterator = content
        self.status_code = status_code
        if media_type is not None:
            self.media_type = media_type
        self.background = background
        self.init_headers(headers)

    async def __call__(self, scope, receive, send):
        await send({
            "type": "http.response.start",
            "status": self.status_code,
            "headers": self.raw_headers,
        })
        
        async for chunk in self.body_iterator:
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            
            await send({
                "type": "http.response.body",
                "body": chunk,
                "more_body": True,
            })
            await asyncio.sleep(0) # 强制让出控制权

        await send({"type": "http.response.body", "body": b"", "more_body": False})
        
        if self.background:
            await self.background()

    
@router.get("/knowledge/files")
async def get_knowledge_files(
    db: Session = Depends(database.get_db),
    current_user: base.UserDB = Depends(deps.get_current_active_admin) # 假设只有管理员能看
):
    """
    获取当前租户的文件列表
    """
    # 关键：必须过滤 tenant_id
    files = db.execute(
        select(base.KnowledgeFile)
        .where(base.KnowledgeFile.tenant_id == current_user.tenant_id)
        .order_by(base.KnowledgeFile.created_at.desc())
    ).scalars().all()
    
    return [
        {
            "id": f.id,
            "filename": f.filename,
            "created_at": f.created_at
        } for f in files
    ]
    

@router.post("/chat")
async def chat_endpoint(
    message: str = Form(...),
    session_id: Optional[int] = Form(None),
    current_user = Depends(deps.get_current_user),
    db: Session = Depends(database.get_db)
):
    # ==========================================
    # 1. 基础校验与会话管理
    # ==========================================
    current_tenant_id = current_user.tenant_id
    if not current_tenant_id:
        raise HTTPException(status_code=400, detail="用户未分配租户")

    # --- 会话处理 ---
    if not session_id:
        new_session = base.ChatSessionDB(
            user_id=current_user.id, 
            title=message[:20],
            tenant_id=current_tenant_id
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        session_id = new_session.id
    else:
        existing_session = db.execute(
            select(base.ChatSessionDB).where(
                base.ChatSessionDB.id == session_id,
                base.ChatSessionDB.user_id == current_user.id, 
                base.ChatSessionDB.tenant_id == current_tenant_id
            )
        ).scalar_one_or_none()

        if not existing_session:
            raise HTTPException(status_code=403, detail="无权访问此会话")

    # 记录用户提问
    user_msg = base.ChatMessageDB(session_id=session_id, role="user", content=message)
    db.add(user_msg)
    db.commit()
    
    try:
        # ==========================================
        # 2. 核心检索逻辑 (RAG)
        # ==========================================
        # 获取向量库实例
        vectorstore = vector_store.get_vectorstore(current_tenant_id)
        
        # 获取混合检索器
        # 注意：get_hybrid_retriever 应该已经修改为支持 tenant_id
        hybrid_retriever = get_hybrid_retriever(current_tenant_id, vectorstore, k=10)
        
        final_context = ""
        is_knowledge_base_empty = False
        
        # 尝试检索
        if hybrid_retriever:
            raw_docs = hybrid_retriever.invoke(message)
            
            # 如果有文档，进行重排序
            if raw_docs:
                ranked_docs = global_reranker.rank(message, raw_docs, top_k=3)
                context_list = [doc.page_content for doc in ranked_docs]
                final_context = "\n\n---\n\n".join(context_list)
            else:
                # 检索器存在，但没搜到相关内容（视为空）
                is_knowledge_base_empty = True 
        else:
            # 检索器本身为空（库是空的）
            is_knowledge_base_empty = True

        # ==========================================
        # 3. 构建 Prompt (核心优化部分)
        # ==========================================
        
        # 定义系统提示词的前缀（通用规则）
        system_prefix = "你是一个智能助手。请根据以下提供的【参考信息】回答用户的【问题】。\n"
        
        # 根据是否有知识库内容，动态构建 Prompt 策略
        if is_knowledge_base_empty:
            # === 场景 A：知识库为空，切换到通用模式 ===
            # 策略：明确告知 LLM 忽略参考信息，使用通用知识，并强制要求输出免责声明
            prompt_context = "无"
            system_instruction = (
                "【重要提示】当前用户的私有知识库中没有相关文档。\n"
                "请完全基于你自身的通用训练数据来回答用户的问题。\n"
                "必须在回答的开头第一句明确提示：“（提示：未在当前知识库找到相关信息，以下是基于通用大模型的参考建议）”。"
            )
        else:
            # === 场景 B：知识库正常，标准 RAG 模式 ===
            # 策略：严格限制 LLM 只能根据参考信息回答
            prompt_context = final_context
            system_instruction = (
                "请严格依据上述【参考信息】回答。如果参考信息无法回答，请说明资料不足，不要编造内容。"
            )

        # 拼接最终的 Prompt 结构
        # 这种结构比单纯把指令塞进 context 更稳定
        final_prompt_template = f"""
        {system_prefix}
        
        {system_instruction}

        【参考信息】:
        {prompt_context}

        【问题】:
        {message}

        【回答】:
        """

        # ==========================================
        # 4. 流式生成
        # ==========================================
        async def event_generator():
            full_response_text = ""
            try:
                rag_chain = get_rag_chain(vectorstore)
                
                # 注意：这里我们将构建好的 final_prompt_template 作为输入
                # 具体取决于你的 get_rag_chain 实现。
                # 如果 get_rag_chain 是标准的 LCEL Runnable，通常接受 dict 输入
                input_data = {
                    # 如果链内部有 template，这里传 context 和 question
                    # 如果链比较灵活，这里可以直接传 input=final_prompt_template
                    # 假设这里我们沿用之前的 context/question 模式，但注入了特殊内容
                    "context": prompt_context, 
                    "question": message
                }
                
                # 如果是自定义链，可能需要把 system_instruction 作为 system_prompt 传入
                # 这里假设我们利用 context 字段的空值或特殊值来触发 LLM 的行为改变
                
                async for chunk in rag_chain.astream(input_data):
                    if chunk:
                        full_response_text += chunk
                        yield f"data: {chunk}\n\n"
                        await asyncio.sleep(0)
                
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"流式生成失败: {e}")
                # 生产环境建议记录到日志系统
                yield f"data: 生成出错: {str(e)}\n\n"
            
            # --- 5. 入库逻辑 ---
            if full_response_text:
                try:
                    ai_msg = base.ChatMessageDB(
                        session_id=session_id, 
                        role="assistant", 
                        content=full_response_text
                    )
                    db.add(ai_msg)
                    db.commit()
                except Exception as e:
                    print(f"入库失败: {e}")
                    db.rollback()

        return NoBufferStreamingResponse(
            event_generator(),
            media_type="text/event-stream;charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
