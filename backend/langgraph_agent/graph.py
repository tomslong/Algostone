"""LangGraph工作流定义 - Production-Ready Edition.

生产级特性:
- 异步执行
- 状态持久化 (checkpointer)
- 流式输出支持
- 中断和恢复能力
"""
from typing import Dict, Any, Optional, AsyncIterator
from pathlib import Path

from langgraph.graph import StateGraph, END, START
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
from langgraph.checkpoint.memory import MemorySaver

from langgraph_agent.state import AgentState
from langgraph_agent.nodes import (
    intent_recognition_node,
    error_diagnosis_node,
    stepwise_hint_node,
    code_comparison_node,
)


# ============================================================================
# Checkpointer配置
# ============================================================================

def get_checkpointer(checkpointer_type: str = "memory"):
    """
    获取状态持久化checkpointer.

    Args:
        checkpointer_type: "memory" 或 "sqlite"

    Returns:
        Checkpointer实例
    """
    if checkpointer_type == "sqlite" and SQLITE_AVAILABLE:
        # 创建checkpoint目录
        checkpoint_dir = Path("data/checkpoints")
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        db_path = checkpoint_dir / "agent_checkpoints.db"
        checkpointer = SqliteSaver(str(db_path))
    else:
        # 内存存储 (适合开发/测试)
        checkpointer = MemorySaver()

    return checkpointer


# ============================================================================
# Agent工作流创建
# ============================================================================

def create_agent_graph(
    checkpointer_type: str = "memory",
    enable_debug: bool = False,
):
    """
    创建生产级Agent工作流图.

    流程:
    START -> 意图识别 -> [有代码?] -> 是 -> 错误诊断 -> 生成回复 -> 结束
                      -> 否 -> 生成回复 -> 结束

    Args:
        checkpointer_type: checkpointer类型 ("memory" 或 "sqlite")
        enable_debug: 是否启用调试模式

    Returns:
        Compiled Runnable对象
    """
    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("intent_recognition", intent_recognition_node)
    workflow.add_node("error_diagnosis", error_diagnosis_node)
    workflow.add_node("stepwise_hint", stepwise_hint_node)
    workflow.add_node("code_comparison", code_comparison_node)

    # 设置入口点
    workflow.set_entry_point("intent_recognition")

    # 条件边：根据是否有代码决定是否执行错误诊断
    workflow.add_conditional_edges(
        "intent_recognition",
        lambda state: "skip_diagnosis" if not state.get('user_code') else "with_diagnosis",
        {
            "skip_diagnosis": "stepwise_hint",  # 无代码，跳过诊断，直接生成回复
            "with_diagnosis": "error_diagnosis",  # 有代码，执行错误诊断
        }
    )

    workflow.add_edge("error_diagnosis", "stepwise_hint")
    workflow.add_edge("stepwise_hint", "code_comparison")

    # 条件边：根据should_end决定是否循环或结束
    workflow.add_conditional_edges(
        "code_comparison",
        lambda state: "end" if state.get('should_end', False) else "continue",
        {
            "end": END,
            "continue": "stepwise_hint"
        }
    )

    # 获取checkpointer
    checkpointer = get_checkpointer(checkpointer_type)

    # 编译图
    app = workflow.compile(
        checkpointer=checkpointer,
        debug=enable_debug
    )

    return app


# ============================================================================
# 全局实例
# ============================================================================

# 生产环境使用SQLite持久化
agent_graph = create_agent_graph(checkpointer_type="sqlite")

# 开发环境可以使用内存存储
# agent_graph = create_agent_graph(checkpointer_type="memory")


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    "create_agent_graph",
    "agent_graph",
    "get_checkpointer",
]
