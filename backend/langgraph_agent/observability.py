"""LangSmith可观测性模块.

提供:
- 自动追踪
- 性能监控
- 调试支持
"""
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langgraph_agent.llm import get_llm

from app.core.config import settings


# ============================================================================
# LangSmith配置
# ============================================================================

def init_langsmith(
    project_name: Optional[str] = None,
    enabled: bool = True,
):
    """
    初始化LangSmith追踪.

    Args:
        project_name: 项目名称，默认为"algostone"
        enabled: 是否启用追踪

    Environment Variables:
        LANGCHAIN_TRACING_V2: 是否启用LangSmith (true/false)
        LANGCHAIN_API_KEY: LangSmith API密钥
        LANGCHAIN_PROJECT: 项目名称
    """
    if not enabled:
        return

    # 检查环境变量
    api_key = os.environ.get("LANGCHAIN_API_KEY")
    if not api_key:
        # 如果没有API key，不启用追踪
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        return

    # 设置环境变量
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault(
        "LANGCHAIN_PROJECT",
        project_name or os.environ.get("LANGCHAIN_PROJECT", "algostone")
    )

    print(f"LangSmith tracing enabled for project: {os.environ['LANGCHAIN_PROJECT']}")


# ============================================================================
# 自动初始化
# ============================================================================

def get_tracing_config() -> dict:
    """
    获取追踪配置.

    Returns:
        包含追踪设置的字典
    """
    return {
        "tracing_enabled": os.environ.get("LANGCHAIN_TRACING_V2", "false").lower() == "true",
        "project_name": os.environ.get("LANGCHAIN_PROJECT", "algostone"),
        "endpoint": os.environ.get("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
    }


# ============================================================================
# 带追踪的LLM包装器
# ============================================================================

def get_traced_llm(
    streaming: bool = True,
    temperature: Optional[float] = None,
    tags: Optional[list] = None,
):
    """
    获取带追踪的LLM实例.

    Args:
        streaming: 是否支持流式输出
        temperature: 温度参数
        tags: 追踪标签

    Returns:
        带LangSmith追踪的LLM实例
    """
    llm = get_llm(streaming=streaming, temperature=temperature)

    # 添加标签用于追踪
    if tags:
        llm.tags = tags

    return llm


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "init_langsmith",
    "get_tracing_config",
    "get_traced_llm",
]
