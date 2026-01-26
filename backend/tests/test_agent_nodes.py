"""Agent节点单元测试."""
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage

from langgraph_agent.nodes import (
    intent_recognition_node,
    error_diagnosis_node,
    stepwise_hint_node,
    code_comparison_node
)
from app.models.schemas import IntentType

@pytest.fixture
def mock_llm():
    with patch('langgraph_agent.nodes.llm') as mock:
        yield mock

@pytest.fixture
def mock_executor():
    with patch('langgraph_agent.nodes.executor') as mock:
        yield mock

@pytest.fixture
def mock_retriever():
    with patch('langgraph_agent.nodes.retriever') as mock:
        yield mock

def test_intent_recognition_node_submit_code(mock_llm):
    """测试意图识别：提交代码."""
    mock_llm.invoke.return_value = AIMessage(content="submit_code")
    
    state = {
        'user_message': "请帮我看看这段代码",
        'user_code': "def solve(): pass",
        'conversation_history': []
    }
    
    result = intent_recognition_node(state)
    
    assert result['intent'] == IntentType.SUBMIT_CODE
    assert result['current_node'] == 'error_diagnosis'

def test_intent_recognition_node_ask_concept(mock_llm):
    """测试意图识别：询问概念."""
    mock_llm.invoke.return_value = AIMessage(content="ask_concept")
    
    state = {
        'user_message': "什么是动态规划？",
        'conversation_history': []
    }
    
    result = intent_recognition_node(state)
    
    assert result['intent'] == IntentType.ASK_CONCEPT

def test_error_diagnosis_node_with_error(mock_executor):
    """测试错误诊断：有错误."""
    # 模拟执行结果
    mock_result = MagicMock()
    mock_result.status = "error"
    mock_result.error_type = "SyntaxError"
    mock_result.error_message = "invalid syntax"
    mock_result.output = ""
    mock_result.execution_time = 0.1
    
    mock_executor.execute_code.return_value = mock_result
    
    state = {
        'intent': IntentType.SUBMIT_CODE,
        'user_code': "def solve(): pass",
        'problem_id': "1"
    }
    
    result = error_diagnosis_node(state)
    
    assert result['has_error'] is True
    assert result['error_type'] == "SyntaxError"
    assert result['test_passed'] is False

def test_error_diagnosis_node_success(mock_executor):
    """测试错误诊断：执行成功."""
    # 模拟执行结果
    mock_result = MagicMock()
    mock_result.status = "success"
    mock_result.output = "10"
    mock_result.execution_time = 0.1
    
    mock_executor.execute_code.return_value = mock_result
    
    state = {
        'intent': IntentType.SUBMIT_CODE,
        'user_code': "print(10)",
        'problem_id': "1"
    }
    
    result = error_diagnosis_node(state)
    
    assert result['has_error'] is False
    assert result['test_passed'] is True

def test_stepwise_hint_node_generation(mock_llm, mock_retriever):
    """测试提示生成."""
    mock_llm.invoke.return_value = AIMessage(content="这是一个提示")
    mock_retriever.retrieve.return_value = []
    
    state = {
        'intent': IntentType.REQUEST_HINT,
        'user_message': "给个提示",
        'current_hint_level': 0,
        'hints_given': []
    }
    
    result = stepwise_hint_node(state)
    
    assert result['current_hint_level'] == 1
    assert result['agent_response'] == "这是一个提示"
    assert len(result['hints_given']) == 1

def test_code_comparison_node_pass():
    """测试代码对比：通过测试."""
    state = {
        'test_passed': True,
        'agent_response': "Good job"
    }
    
    result = code_comparison_node(state)
    
    assert result['should_end'] is True
    assert "通过了所有测试用例" in state['agent_response']

def test_code_comparison_node_retry():
    """测试代码对比：需要重试."""
    state = {
        'test_passed': False,
        'max_hint_reached': False,
        'attempt_count': 0,
        'agent_response': "Try again"
    }
    
    result = code_comparison_node(state)
    
    assert result['should_end'] is False
    assert result['attempt_count'] == 1
