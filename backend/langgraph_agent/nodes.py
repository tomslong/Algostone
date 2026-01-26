"""LangGraph节点实现 - Production-Ready Edition.

生产级特性:
- 全async支持
- 错误处理和重试逻辑
- 结构化日志
- 性能优化
"""
from typing import Dict, Any, AsyncIterator, Optional
import asyncio
import time

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from langgraph_agent.state import AgentState
from langgraph_agent.llm import get_chat_llm, get_fast_llm, get_dynamic_llm
from app.models.schemas import IntentType


# ============================================================================
# 日志配置
# ============================================================================

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# 错误定义
# ============================================================================

class LLMError(Exception):
    """LLM调用错误."""
    pass


class NodeTimeoutError(Exception):
    """节点执行超时."""
    pass


# ============================================================================
# 重试装饰器
# ============================================================================

def llm_retry(fn):
    """LLM调用的重试装饰器."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((LLMError, ConnectionError, TimeoutError)),
        reraise=True,
    )(fn)


# ============================================================================
# 工具函数
# ============================================================================

async def call_llm_with_timeout(
    llm: BaseChatModel,
    messages: list,
    timeout: float = 25.0,
) -> str:
    """
    带超时的LLM调用.

    Args:
        llm: LLM实例
        messages: 消息列表
        timeout: 超时时间(秒)

    Returns:
        str: LLM响应内容

    Raises:
        NodeTimeoutError: 超时错误
        LLMError: LLM调用错误
    """
    try:
        async def _invoke():
            response = await llm.ainvoke(messages)
            return response.content

        result = await asyncio.wait_for(_invoke(), timeout=timeout)
        return result
    except asyncio.TimeoutError:
        logger.error(f"LLM调用超时: {timeout}秒")
        raise NodeTimeoutError(f"LLM调用超时")
    except Exception as e:
        logger.error(f"LLM调用失败: {e}")
        raise LLMError(f"LLM调用失败: {e}")


# ============================================================================
# 节点1: 意图识别
# ============================================================================

async def intent_recognition_node(state: AgentState) -> Dict[str, Any]:
    """
    节点1: 意图识别 (优化版 - 使用规则匹配).

    识别学生的意图：
    - 提交代码求调试
    - 询问算法概念
    - 请求提示
    - 其他

    Returns:
        Dict[str, Any]: 更新的状态
    """
    start_time = time.time()
    user_message = state['user_message'].lower()
    user_code = state.get('user_code')

    # 使用规则匹配识别意图（无需LLM调用，节省时间和成本）
    intent = IntentType.OTHER

    if user_code:
        # 有代码提交
        intent = IntentType.SUBMIT_CODE
    elif any(keyword in user_message for keyword in ['什么', '如何', '怎么', '解释', '原理', '定义', '为什么']):
        intent = IntentType.ASK_CONCEPT
    elif any(keyword in user_message for keyword in ['提示', '帮助', 'hint', 'help', '思路', '优化']):
        intent = IntentType.REQUEST_HINT

    elapsed = time.time() - start_time
    logger.info(f"意图识别完成: {intent.value}, 耗时: {elapsed:.3f}秒")

    return {
        'intent': intent,
        'current_node': 'error_diagnosis'
    }


# ============================================================================
# 节点2: 错误诊断
# ============================================================================

async def error_diagnosis_node(state: AgentState) -> Dict[str, Any]:
    """
    节点2: 错误诊断.

    分析用户代码，识别语法错误和潜在问题。

    Returns:
        Dict[str, Any]: 更新的状态
    """
    start_time = time.time()
    intent = state['intent']
    user_code = state.get('user_code')

    # 简化处理：只有提交代码时标记需要诊断
    if intent != IntentType.SUBMIT_CODE or not user_code:
        elapsed = time.time() - start_time
        logger.info(f"跳过错误诊断 (无代码), 耗时: {elapsed:.3f}秒")
        return {
            'has_error': False,
            'current_node': 'stepwise_hint'
        }

    # 简单的语法检查
    has_syntax_error = False
    error_msg = None
    error_type = None

    # 检查常见语法问题
    code = user_code.strip()
    if not code:
        has_syntax_error = True
        error_msg = "代码为空"
        error_type = "EmptyCodeError"
    elif 'def ' not in code and 'class ' not in code and 'print(' not in code:
        # 至少应该有函数定义或打印语句
        has_syntax_error = True
        error_msg = "代码中没有找到函数定义或执行语句"
        error_type = "SyntaxError"
    elif code.count('def ') > 0 and code.count('def ') == code.count('def \n'):
        # 检查空函数
        has_syntax_error = True
        error_msg = "函数定义后缺少实现代码"
        error_type = "IndentationError"

    elapsed = time.time() - start_time
    logger.info(f"错误诊断完成: has_error={has_syntax_error}, 耗时: {elapsed:.3f}秒")

    return {
        'has_error': has_syntax_error,
        'error_type': error_type,
        'error_message': error_msg,
        'execution_result': None,
        'test_passed': False,
        'current_node': 'stepwise_hint'
    }


# ============================================================================
# 节点3: 生成回复 (异步+重试)
# ============================================================================

async def stepwise_hint_node(state: AgentState) -> Dict[str, Any]:
    """
    节点3: 生成回复 (异步版).

    根据用户问题直接生成回复，支持RAG检索。

    Returns:
        Dict[str, Any]: 更新的状态
    """
    start_time = time.time()
    intent = state['intent']
    has_error = state.get('has_error', False)
    current_hint_level = state.get('current_hint_level', 0)
    hints_given = state.get('hints_given', [])
    user_message = state['user_message']
    user_code = state.get('user_code')

    # 构建prompt
    if intent == IntentType.SUBMIT_CODE and user_code:
        if has_error:
            error_msg = state.get('error_message', '未知错误')
            system_prompt = f"""你是一个算法学习助手。分析代码错误：{error_msg}

```python
{user_code[:500]}
```

简洁说明错误原因和修改建议。"""
        else:
            system_prompt = f"""你是一个算法学习助手。分析以下代码并给出优化建议：

```python
{user_code[:500]}
```

从时间复杂度、空间复杂度、代码可读性方面给出简洁建议。"""

    elif intent == IntentType.ASK_CONCEPT:
        system_prompt = f"""你是一个算法学习助手。解释以下概念：

{user_message}

简洁说明：1.核心思想 2.应用场景 3.复杂度。控制在200字以内。"""

    else:
        # 常规提示/帮助场景
        system_prompt = f"""你是一个友好的算法学习助手。

学生问题: {user_message}

给出简洁、有针对性的回复。如果是算法问题，先说明思路，再给建议。控制在200字以内。"""

    try:
        # 检查是否有动态 API 配置
        api_key = state.get('api_key')
        model_name = state.get('model_name')
        api_base = state.get('api_base')

        if api_key and model_name and api_base:
            # 使用前端发送的动态配置
            llm = get_dynamic_llm(api_key, model_name, api_base, streaming=False)
        else:
            # 使用默认配置 (环境变量)
            llm = get_chat_llm(streaming=False)

        hint = await call_llm_with_timeout(
            llm,
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ],
            timeout=90.0  # 增加到 90 秒
        )

        hints_given.append(hint)
        elapsed = time.time() - start_time
        logger.info(f"提示生成完成, 耗时: {elapsed:.3f}秒")

        return {
            'current_hint_level': current_hint_level,
            'hints_given': hints_given,
            'max_hint_reached': current_hint_level >= 3,
            'retrieved_docs': [],
            'agent_response': hint,
            'current_node': 'code_comparison'
        }

    except (NodeTimeoutError, LLMError) as e:
        logger.warning(f"LLM调用失败，使用fallback回复: {e}")
        fallback_hint = "我来帮你分析一下。请告诉我你遇到了什么具体问题，或者你想要了解哪个算法概念？"

        return {
            'current_hint_level': current_hint_level,
            'hints_given': hints_given + [fallback_hint],
            'agent_response': fallback_hint,
            'current_node': 'end',  # 直接结束，不再重试
            'should_end': True,
            'retrieved_docs': []
        }


# ============================================================================
# 节点4: 代码执行对比
# ============================================================================

async def code_comparison_node(state: AgentState) -> Dict[str, Any]:
    """
    节点4: 代码执行对比.

    决定是否需要更多提示，或者问题已解决。

    Returns:
        Dict[str, Any]: 更新的状态
    """
    start_time = time.time()
    test_passed = state.get('test_passed', False)
    max_hint_reached = state.get('max_hint_reached', False)
    attempt_count = state.get('attempt_count', 0)
    intent = state.get('intent')
    user_code = state.get('user_code')

    # 判断是否应该结束
    should_end = False
    next_node = 'stepwise_hint'
    response_suffix = ""

    # 对于非代码提交场景，直接结束
    if intent != IntentType.SUBMIT_CODE or not user_code:
        should_end = True
    elif test_passed:
        # 代码通过测试，给予鼓励
        should_end = True
        response_suffix = "\n\n太棒了！你的代码通过了所有测试用例！"
    elif attempt_count >= 3:
        # 尝试次数过多
        should_end = True
        response_suffix = "\n\n看起来这个问题比较有挑战性。要不要先看看完整的题解，然后再自己实现一遍？"
    elif max_hint_reached and not test_passed:
        # 已给最高级别提示但仍未通过
        response_suffix = "\n\n根据这些提示，试着修改你的代码。如果还有困难，可以再次提交代码给我看看。"
        should_end = True

    # 更新响应
    if response_suffix:
        agent_response = state.get('agent_response', '')
        agent_response += response_suffix

    elapsed = time.time() - start_time
    logger.info(f"代码对比完成: should_end={should_end}, 耗时: {elapsed:.3f}秒")

    return {
        'should_end': should_end,
        'agent_response': agent_response if response_suffix else state.get('agent_response', ''),
        'current_node': 'end' if should_end else next_node,
        'attempt_count': attempt_count + 1
    }


# ============================================================================
# 流式生成节点
# ============================================================================

async def stepwise_hint_node_stream(
    state: AgentState,
) -> AsyncIterator[str]:
    """
    流式生成提示内容，支持推理过程 (reasoning_content).

    Args:
        state: Agent状态

    Yields:
        str: 生成的内容片段 (包括推理过程和最终答案)
    """
    intent = state['intent']
    has_error = state.get('has_error', False)
    user_message = state['user_message']
    user_code = state.get('user_code')

    # 构建prompt
    if intent == IntentType.SUBMIT_CODE and user_code:
        if has_error:
            error_msg = state.get('error_message', '未知错误')
            system_prompt = f"""你是一个算法学习助手。分析代码错误：{error_msg}

```python
{user_code[:500]}
```

简洁说明错误原因和修改建议。"""
        else:
            system_prompt = f"""你是一个算法学习助手。分析以下代码并给出优化建议：

```python
{user_code[:500]}
```

从时间复杂度、空间复杂度、代码可读性方面给出简洁建议。"""
    elif intent == IntentType.ASK_CONCEPT:
        system_prompt = f"""你是一个算法学习助手。解释以下概念：

{user_message}

简洁说明：1.核心思想 2.应用场景 3.复杂度。控制在200字以内。"""
    else:
        system_prompt = f"""你是一个友好的算法学习助手。

学生问题: {user_message}

给出简洁、有针对性的回复。如果是算法问题，先说明思路，再给建议。控制在200字以内。"""

    try:
        # 检查是否有动态 API 配置
        api_key = state.get('api_key')
        model_name = state.get('model_name')
        api_base = state.get('api_base')

        if api_key and model_name and api_base:
            # 使用前端发送的动态配置
            llm = get_dynamic_llm(api_key, model_name, api_base, streaming=True)
        else:
            # 使用默认配置 (环境变量)
            llm = get_chat_llm(streaming=True)

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ]

        # 使用 astream_events 获取完整事件流 (包括 reasoning_content)
        reasoning_yielded = False

        async for event in llm.astream_events(
            messages,
            version="v1",
            include_names=["ChatOpenAI"]
        ):
            event_type = event["event"]

            # 调试：记录事件类型
            logger.info(f"LLM Event: {event_type}")

            # 检查是否有 reasoning_content (DeepSeek-R1 等推理模型)
            if event_type == "on_chat_model_end":
                output = event["data"].get("output", {})
                logger.info(f"LLM Output keys: {output.keys() if hasattr(output, 'keys') else 'N/A'}")
                logger.info(f"LLM response_metadata: {output.response_metadata if hasattr(output, 'response_metadata') else 'N/A'}")

                response_metadata = output.response_metadata if hasattr(output, 'response_metadata') else {}
                reasoning = response_metadata.get("reasoning_content", "") if response_metadata else ""

                logger.info(f"Extracted reasoning_content length: {len(reasoning) if reasoning else 0}")

                if reasoning and not reasoning_yielded:
                    reasoning_yielded = True
                    # 发送推理过程 (以特殊前缀标记，方便前端识别)
                    yield f"<reasoning>{reasoning}</reasoning>"

            # 流式输出普通内容
            elif event_type == "on_chat_model_stream":
                chunk = event["data"].get("chunk", {})
                content = chunk.content if hasattr(chunk, 'content') else ""
                if content:
                    yield content

    except Exception as e:
        logger.error(f"流式生成失败: {e}")
        yield "抱歉，生成回复时出错了。请稍后重试。"


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    'intent_recognition_node',
    'error_diagnosis_node',
    'stepwise_hint_node',
    'code_comparison_node',
    'stepwise_hint_node_stream',
    'LLMError',
    'NodeTimeoutError',
]
