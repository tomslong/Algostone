"""聊天对话路由 - Production-Ready Edition.

支持:
- 非流式聊天 (ainvoke)
- 流式聊天 (astream_events)
- 会话历史管理（PostgreSQL存储）
- 错误处理和降级
"""
import logging
import json
import time
from typing import AsyncIterator, Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.models.schemas import ChatRequest, ChatResponse
from langgraph_agent.graph import agent_graph
from langgraph_agent.state import AgentState
from langgraph_agent.llm import get_llm
from langgraph_agent.nodes import stepwise_hint_node_stream
from app.core.security import sanitize_for_log
from app.core.config import settings
from app.core.database import db

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# 请求/响应模型
# ============================================================================

class StreamChatRequest(BaseModel):
    """流式聊天请求."""
    message: str = Field(..., description="用户消息")
    code: Optional[str] = Field(None, description="可选的代码片段")
    problem_id: Optional[str] = Field(None, description="题目ID")
    session_id: str = Field(..., description="会话ID，用于保持上下文")
    conversation_history: list = Field(default_factory=list, description="对话历史")
    # 动态 API 配置
    api_key: Optional[str] = Field(None, description="API密钥")
    model_name: Optional[str] = Field(None, description="模型名称")
    api_base: Optional[str] = Field(None, description="API地址")


class ChatRequestWithSession(ChatRequest):
    """带会话ID的聊天请求."""
    session_id: str = Field(default="default", description="会话ID")


# ============================================================================
# 非流式聊天端点
# ============================================================================

@router.post("/send", response_model=ChatResponse)
async def send_message(http_request: Request, request: ChatRequestWithSession):
    """
    发送消息给AI智能体 (非流式).

    Args:
        request: 聊天请求

    Returns:
        ChatResponse: AI响应
    """
    start_time = time.time()
    logger.info(f"收到聊天请求: session_id={request.session_id}, message={sanitize_for_log(request.message)}")

    # 保存用户消息到数据库
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chat_messages (session_id, task_id, role, content)
                VALUES (%s, %s, %s, %s)
            """, (request.session_id, request.problem_id, "user", request.message))
            conn.commit()
    except Exception as e:
        logger.error(f"保存用户消息失败: {e}")

    try:
        # 构建初始状态
        initial_state: AgentState = {
            "session_id": request.session_id,
            "problem_id": request.problem_id,
            "user_message": request.message,
            "user_code": request.code,
            "conversation_history": request.conversation_history or [],
            # 动态 API 配置
            "api_key": request.api_key,
            "model_name": request.model_name,
            "api_base": request.api_base,
            # 其他状态
            "intent": None,
            "has_error": False,
            "error_type": None,
            "error_message": None,
            "error_line": None,
            "current_hint_level": 0,
            "hints_given": [],
            "max_hint_reached": False,
            "execution_result": None,
            "test_passed": False,
            "retrieved_docs": [],
            "agent_response": "",
            "current_node": "",
            "attempt_count": 0,
            "should_end": False,
        }

        # 执行agent工作流
        config = {"configurable": {"thread_id": request.session_id}}

        result = await agent_graph.ainvoke(
            initial_state,
            config=config
        )

        elapsed = time.time() - start_time
        logger.info(f"聊天完成: session_id={request.session_id}, 耗时={elapsed:.3f}秒")

        agent_response = result.get("agent_response", "")

        # 保存AI回复到数据库
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO chat_messages (session_id, task_id, role, content)
                    VALUES (%s, %s, %s, %s)
                """, (request.session_id, request.problem_id, "assistant", agent_response))
                conn.commit()
        except Exception as e:
            logger.error(f"保存AI回复失败: {e}")

        # 构建响应
        return ChatResponse(
            message=agent_response,
            hint_level=result.get("current_hint_level", 0),
            code_execution_result=result.get("execution_result"),
            suggested_resources=[],
            intent=result.get("intent", "other").value if result.get("intent") else "other"
        )

    except Exception as e:
        logger.error(f"聊天处理失败: {e}", exc_info=True)
        elapsed = time.time() - start_time

        # 降级响应
        return ChatResponse(
            message=f"抱歉，系统处理时出现了错误。请稍后再试。",
            hint_level=0,
            suggested_resources=[],
            intent="error"
        )


# ============================================================================
# 流式聊天端点
# ============================================================================

@router.post("/stream")
async def send_message_stream(request: StreamChatRequest):
    """
    发送消息给AI智能体 (流式输出).

    返回Server-Sent Events (SSE)格式的流式响应。

    Args:
        request: 流式聊天请求

    Returns:
        StreamingResponse: SSE流式响应

    Example:
        ```python
        async with client.stream("POST", "/api/v1/chat/stream", json={
            "message": "解释一下快速排序",
            "session_id": "user_123"
        }) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    print(data.get("content", ""), end="")
        ```
    """
    logger.info(f"收到流式聊天请求: session_id={request.session_id}")

    async def event_stream() -> AsyncIterator[str]:
        """生成SSE事件流."""
        # 先保存用户消息到数据库
        try:
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO chat_messages (session_id, task_id, role, content)
                    VALUES (%s, %s, %s, %s)
                """, (request.session_id, request.problem_id, "user", request.message))
                conn.commit()
                logger.info(f"用户消息已保存: session_id={request.session_id}")
        except Exception as e:
            logger.error(f"保存用户消息失败: {e}")

        try:
            # 发送开始事件
            yield f"data: {json.dumps({'type': 'start', 'session_id': request.session_id})}\n\n"

            # 先执行意图识别和错误诊断（非流式部分）
            initial_state: AgentState = {
                "session_id": request.session_id,
                "problem_id": request.problem_id,
                # 动态 API 配置
                "api_key": request.api_key,
                "model_name": request.model_name,
                "api_base": request.api_base,
                # 用户输入
                "user_message": request.message,
                "user_code": request.code,
                "conversation_history": request.conversation_history,
                # 其他状态
                "intent": None,
                "has_error": False,
                "error_type": None,
                "error_message": None,
                "error_line": None,
                "current_hint_level": 0,
                "hints_given": [],
                "max_hint_reached": False,
                "execution_result": None,
                "test_passed": False,
                "retrieved_docs": [],
                "agent_response": "",
                "current_node": "",
                "attempt_count": 0,
                "should_end": False,
            }

            # 执行非流式节点
            from langgraph_agent.nodes import intent_recognition_node, error_diagnosis_node

            # 意图识别
            intent_result = await intent_recognition_node(initial_state)
            initial_state.update(intent_result)
            yield f"data: {json.dumps({'type': 'intent', 'intent': initial_state['intent'].value})}\n\n"

            # 错误诊断 (如果有代码)
            if initial_state.get('user_code'):
                diagnosis_result = await error_diagnosis_node(initial_state)
                initial_state.update(diagnosis_result)
                yield f"data: {json.dumps({'type': 'diagnosis', 'has_error': initial_state['has_error']})}\n\n"

            # 流式生成回复
            yield f"data: {json.dumps({'type': 'content_start'})}\n\n"

            full_content = []
            reasoning_content = []
            in_reasoning = False

            async for chunk in stepwise_hint_node_stream(initial_state):
                if chunk:
                    # 检查是否包含推理标签
                    if "<reasoning>" in chunk:
                        in_reasoning = True
                        parts = chunk.split("<reasoning>", 1)
                        if parts[0]:  # 标签前的内容
                            full_content.append(parts[0])
                            yield f"data: {json.dumps({'type': 'content', 'content': parts[0]})}\n\n"
                        if len(parts) > 1:
                            remaining = parts[1]
                            if "</reasoning>" in remaining:
                                in_reasoning = False
                                reason_parts = remaining.split("</reasoning>", 1)
                                reasoning_content.append(reason_parts[0])
                                # 发送完整的推理过程
                                full_reasoning = ''.join(reasoning_content)
                                yield f"data: {json.dumps({'type': 'reasoning', 'content': full_reasoning})}\n\n"
                                if reason_parts[1]:  # 标签后的内容
                                    full_content.append(reason_parts[1])
                                    yield f"data: {json.dumps({'type': 'content', 'content': reason_parts[1]})}\n\n"
                            else:
                                reasoning_content.append(remaining)
                        continue

                    if "</reasoning>" in chunk:
                        in_reasoning = False
                        parts = chunk.split("</reasoning>", 1)
                        reasoning_content.append(parts[0])
                        # 发送完整的推理过程
                        full_reasoning = ''.join(reasoning_content)
                        yield f"data: {json.dumps({'type': 'reasoning', 'content': full_reasoning})}\n\n"
                        if parts[1]:  # 标签后的内容
                            full_content.append(parts[1])
                            yield f"data: {json.dumps({'type': 'content', 'content': parts[1]})}\n\n"
                        continue

                    if in_reasoning:
                        reasoning_content.append(chunk)
                    else:
                        full_content.append(chunk)
                        # 发送内容片段
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

            # 保存AI回复到数据库 (不包含 reasoning 标签)
            assistant_message = ''.join(full_content)
            # 移除可能残留的标签
            assistant_message = assistant_message.replace("<reasoning>", "").replace("</reasoning>", "")
            if assistant_message:
                try:
                    with db.get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO chat_messages (session_id, task_id, role, content)
                            VALUES (%s, %s, %s, %s)
                        """, (request.session_id, request.problem_id, "assistant", assistant_message))
                        conn.commit()
                        logger.info(f"AI回复已保存: session_id={request.session_id}")
                except Exception as e:
                    logger.error(f"保存AI回复失败: {e}")

            # 发送结束事件
            yield f"data: {json.dumps({'type': 'end'})}\n\n"

        except Exception as e:
            logger.error(f"流式聊天错误: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ============================================================================
# 简化版端点 (直接LLM调用，不走LangGraph)
# ============================================================================

@router.post("/simple", response_model=ChatResponse)
async def send_message_simple(http_request: Request, request: ChatRequest):
    """
    简化版聊天端点 - 直接调用LLM，不使用LangGraph.

    适用于简单场景，无需复杂的状态管理。
    """
    logger.info(f"收到简单聊天请求: message={sanitize_for_log(request.message)}")

    try:
        llm = get_llm(streaming=False)

        from langchain_core.messages import HumanMessage, SystemMessage

        user_message = request.message
        user_code = request.code or ""

        # 构建prompt
        if user_code:
            prompt = f"""你是一个算法学习助手。学生提交了代码：

```python
{user_code[:800]}
```

学生问题: {user_message}

给出简洁的分析和建议（200字以内）。"""
        else:
            prompt = f"""你是一个友好的算法学习助手。

学生问题: {user_message}

给出简洁、有针对性的回复。如果是算法问题，先说明思路，再给建议。控制在200字以内。"""

        response = await llm.ainvoke([
            SystemMessage(content="你是一个算法学习助手，回复要简洁专业。"),
            HumanMessage(content=prompt)
        ])

        return ChatResponse(
            message=response.content.strip(),
            hint_level=None,
            code_execution_result=None,
            suggested_resources=[],
            intent="answer"
        )

    except Exception as e:
        logger.error(f"简单聊天失败: {e}", exc_info=True)
        return ChatResponse(
            message=f"抱歉，系统处理时出现了错误。请稍后再试。",
            hint_level=0,
            suggested_resources=[],
            intent="error"
        )


# ============================================================================
# 会话管理端点
# ============================================================================

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话历史.

    Args:
        session_id: 会话ID

    Returns:
        删除结果
    """
    try:
        # LangGraph的checkpointer会自动管理状态
        # 这里可以添加额外的清理逻辑
        logger.info(f"删除会话: session_id={session_id}")

        return {"status": "success", "message": "会话已删除"}

    except Exception as e:
        logger.error(f"删除会话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session_state(session_id: str):
    """
    获取会话状态.

    Args:
        session_id: 会话ID

    Returns:
        会话状态信息
    """
    try:
        config = {"configurable": {"thread_id": session_id}}

        # 获取checkpoint
        checkpoint = agent_graph.get_state(config)

        if not checkpoint:
            return {"session_id": session_id, "exists": False}

        return {
            "session_id": session_id,
            "exists": True,
            "state": checkpoint.values if checkpoint else None,
        }

    except Exception as e:
        logger.error(f"获取会话状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 聊天消息存储端点 (PostgreSQL)
# ============================================================================

class ChatMessage(BaseModel):
    """聊天消息."""
    id: Optional[int] = None
    session_id: str
    task_id: Optional[str] = None
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str
    created_at: Optional[str] = None


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, task_id: Optional[str] = None):
    """
    获取聊天历史（从数据库）.

    Args:
        session_id: 会话 ID
        task_id: 题目 ID（可选，用于过滤）
    """
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()

            if task_id:
                cur.execute("""
                    SELECT id, session_id, task_id, role, content, created_at
                    FROM chat_messages
                    WHERE session_id = %s AND task_id = %s
                    ORDER BY created_at ASC
                """, (session_id, task_id))
            else:
                cur.execute("""
                    SELECT id, session_id, task_id, role, content, created_at
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY created_at ASC
                """, (session_id,))

            rows = cur.fetchall()
            messages = [
                {
                    "id": row[0],
                    "session_id": row[1],
                    "task_id": row[2],
                    "role": row[3],
                    "content": row[4],
                    "created_at": row[5].isoformat() if row[5] else None
                }
                for row in rows
            ]

        return {"session_id": session_id, "task_id": task_id, "messages": messages}

    except Exception as e:
        logger.error(f"获取聊天历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/messages")
async def save_message(message: ChatMessage):
    """
    保存聊天消息到数据库.

    Args:
        message: 消息内容
    """
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chat_messages (session_id, task_id, role, content)
                VALUES (%s, %s, %s, %s)
                RETURNING id, session_id, task_id, role, content, created_at
            """, (message.session_id, message.task_id, message.role, message.content))

            row = cur.fetchone()
            conn.commit()

        return {
            "id": row[0],
            "session_id": row[1],
            "task_id": row[2],
            "role": row[3],
            "content": row[4],
            "created_at": row[5].isoformat() if row[5] else None
        }

    except Exception as e:
        logger.error(f"保存消息失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{session_id}")
async def clear_chat_history(session_id: str, task_id: Optional[str] = None):
    """
    清空聊天历史.

    Args:
        session_id: 会话 ID
        task_id: 题目 ID（可选，如果提供则只清空该题目的消息）
    """
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()

            if task_id:
                cur.execute("""
                    DELETE FROM chat_messages
                    WHERE session_id = %s AND task_id = %s
                """, (session_id, task_id))
            else:
                cur.execute("""
                    DELETE FROM chat_messages
                    WHERE session_id = %s
                """, (session_id,))

            conn.commit()

        return {"deleted": True, "session_id": session_id, "task_id": task_id}

    except Exception as e:
        logger.error(f"清空聊天历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test")
async def test_chat_db():
    """测试数据库写入."""
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO chat_messages (session_id, task_id, role, content)
                VALUES (%s, %s, %s, %s)
                RETURNING id, created_at
            """, ("test_session", None, "assistant", "Test message from API"))
            result = cur.fetchone()
            conn.commit()

        return {"status": "success", "id": result[0], "created_at": result[1]}

    except Exception as e:
        logger.error(f"测试失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
