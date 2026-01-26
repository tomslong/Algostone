"""LangGraph状态定义 - Production-Ready Edition.

使用最新的LangGraph 0.2+注解语法，支持消息 reducer和状态管理最佳实践。
"""
from typing import TypedDict, List, Optional, Dict, Any, Literal, Annotated
from typing_extensions import Required
from langgraph.graph import MessagesState

from app.models.schemas import IntentType


# ============================================================================
# 核心Agent状态定义
# ============================================================================

class AgentState(TypedDict):
    """
    生产级Agent状态定义.

    使用LangGraph推荐的TypedDict模式，支持:
    - 完整的类型注解
    - Optional字段标记
    - 与checkpointer集成的状态持久化
    """
    # ========================================================================
    # 会话标识 (必需字段)
    # ========================================================================
    session_id: Required[str]
    problem_id: Optional[str]

    # ========================================================================
    # 动态 API 配置 (前端发送的配置)
    # ========================================================================
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    api_base: Optional[str] = None

    # ========================================================================
    # 用户输入
    # ========================================================================
    user_message: str
    user_code: Optional[str]

    # ========================================================================
    # 对话历史 (使用MessagesState模式更佳，这里保持兼容)
    # ========================================================================
    conversation_history: List[Dict[str, str]]

    # ========================================================================
    # 意图识别结果
    # ========================================================================
    intent: Optional[IntentType]

    # ========================================================================
    # 错误诊断信息
    # ========================================================================
    has_error: bool
    error_type: Optional[str]
    error_message: Optional[str]
    error_line: Optional[int]

    # ========================================================================
    # 提示生成状态
    # ========================================================================
    current_hint_level: int
    hints_given: List[str]
    max_hint_reached: bool

    # ========================================================================
    # 代码执行结果
    # ========================================================================
    execution_result: Optional[Dict[str, Any]]
    test_passed: bool

    # ========================================================================
    # RAG检索结果
    # ========================================================================
    retrieved_docs: List[Dict[str, Any]]

    # ========================================================================
    # 最终响应
    # ========================================================================
    agent_response: str

    # ========================================================================
    # 流程控制
    # ========================================================================
    current_node: str
    attempt_count: int
    should_end: bool


# ============================================================================
# 使用MessagesState的简化版本 (推荐用于新实现)
# ============================================================================

class MessagesAgentState(MessagesState):
    """
    基于LangGraph MessagesState的简化状态.

    优势:
    - 内置消息历史管理 (messages字段自动处理)
    - 内置reducer避免消息重复
    - 与LangGraph预构建工具更好集成

    扩展字段用于AlgoStone特定需求.
    """

    # AlgoStone特定字段
    session_id: str
    problem_id: Optional[str]
    user_code: Optional[str]

    # 意图识别
    intent: Optional[IntentType]

    # 错误诊断
    has_error: bool
    error_type: Optional[str]
    error_message: Optional[str]

    # 提示系统
    current_hint_level: int
    max_hint_reached: bool

    # 代码执行
    execution_result: Optional[Dict[str, Any]]
    test_passed: bool

    # RAG检索
    retrieved_docs: List[Dict[str, Any]]


# ============================================================================
# 路由状态定义 (用于条件边)
# ============================================================================

class RouterState(TypedDict):
    """条件路由状态."""

    next_node: Literal[
        "error_diagnosis",
        "stepwise_hint",
        "code_comparison",
        "end",
        "continue"
    ]


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "AgentState",
    "MessagesAgentState",
    "RouterState",
]
