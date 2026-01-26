"""LLM初始化模块 - 支持任何OpenAI兼容API.

用户可通过环境变量配置:
- MODEL_NAME: 模型名称 (如: gpt-4o-mini, deepseek-chat, deepseek-reasoner等)
- API_KEY: API密钥
- MODEL_API_URL: API地址 (如: https://api.openai.com/v1)

支持推理过程显示 (reasoning_content):
- DeepSeek-R1: 返回 reasoning_content 字段，包含模型思考过程
"""
from typing import Optional
from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.core.config import settings


# ============================================================================
# LLM配置
# ============================================================================

DEFAULT_MODEL = "qwen-plus"
DEFAULT_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024  # 减少以加快响应速度
DEFAULT_TIMEOUT = 60.0


# ============================================================================
# LLM初始化函数
# ============================================================================

@lru_cache(maxsize=1)
def get_llm(
    streaming: bool = True,
    temperature: Optional[float] = None,
) -> BaseChatModel:
    """
    获取LLM实例 (单例模式).

    从环境变量读取配置:
    - MODEL_NAME: 模型名称
    - API_KEY: API密钥 (必需)
    - MODEL_API_URL: API地址

    Args:
        streaming: 是否支持流式输出
        temperature: 温度参数，默认使用配置值

    Returns:
        BaseChatModel: LLM实例

    Raises:
        ValueError: 未设置API密钥

    Examples:
        # .env 文件配置示例:
        # 使用通义千问
        MODEL_NAME=qwen-plus
        API_KEY=sk-xxx
        MODEL_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

        # 使用DeepSeek
        MODEL_NAME=deepseek-chat
        API_KEY=sk-xxx
        MODEL_API_URL=https://api.deepseek.com/v1

        # 使用OpenAI
        MODEL_NAME=gpt-4o-mini
        API_KEY=sk-xxx
        MODEL_API_URL=https://api.openai.com/v1

        # 使用任何其他OpenAI兼容API
        MODEL_NAME=your-model-name
        API_KEY=your-api-key
        MODEL_API_URL=https://your-api-endpoint.com/v1
    """
    api_key = settings.API_KEY
    if not api_key:
        raise ValueError("未设置 API_KEY 环境变量")

    llm = ChatOpenAI(
        model=settings.MODEL_NAME or DEFAULT_MODEL,
        temperature=temperature if temperature is not None else DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
        timeout=DEFAULT_TIMEOUT,
        api_key=api_key,
        base_url=settings.MODEL_API_URL or DEFAULT_API_URL,
        streaming=streaming,
    )

    return llm


def get_chat_llm(streaming: bool = True) -> BaseChatModel:
    """获取用于聊天的LLM实例 (支持流式输出)."""
    return get_llm(streaming=streaming)


def get_fast_llm() -> BaseChatModel:
    """获取快速LLM实例 (用于简单任务，不使用流式)."""
    return get_llm(streaming=False, temperature=0.3)


def get_dynamic_llm(
    api_key: str,
    model_name: str,
    api_base: str,
    streaming: bool = False,
) -> BaseChatModel:
    """
    使用动态配置创建LLM实例 (前端发送的配置).

    Args:
        api_key: API密钥
        model_name: 模型名称
        api_base: API地址
        streaming: 是否支持流式输出

    Returns:
        BaseChatModel: LLM实例
    """
    llm = ChatOpenAI(
        model=model_name,
        temperature=DEFAULT_TEMPERATURE,
        max_tokens=DEFAULT_MAX_TOKENS,
        timeout=DEFAULT_TIMEOUT,
        api_key=api_key,
        base_url=api_base,
        streaming=streaming,
    )
    return llm


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "get_llm",
    "get_chat_llm",
    "get_fast_llm",
    "get_dynamic_llm",
]
