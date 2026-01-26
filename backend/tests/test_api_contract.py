
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add backend to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.models.schemas import CodeExecutionResult

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "AlgoStone API"}

@patch("app.api.routes.chat.agent_graph")
def test_chat_send_api_contract(mock_agent_graph):
    # Mock LangGraph response
    mock_final_state = {
        "agent_response": "这是一个测试回复",
        "current_hint_level": 1,
        "execution_result": None,
        "intent": "ask_concept",
        "retrieved_docs": []
    }
    
    # Setup async mock
    async def mock_ainvoke(*args, **kwargs):
        return mock_final_state
    
    mock_agent_graph.ainvoke = MagicMock(side_effect=mock_ainvoke)

    payload = {
        "message": "什么是动态规划？",
        "conversation_history": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！有什么我可以帮你的吗？"}
        ]
    }

    response = client.post("/api/chat/send", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure matches ChatResponse schema
    assert "message" in data
    assert "hint_level" in data
    assert "code_execution_result" in data
    assert "suggested_resources" in data
    assert "intent" in data
    
    assert data["message"] == "这是一个测试回复"
    assert data["intent"] == "ask_concept"

@patch("app.api.routes.execute.executor")
def test_execute_code_api_contract(mock_executor):
    # Mock Executor response
    mock_result = CodeExecutionResult(
        status="success",
        output="Hello World",
        execution_time=0.1,
        memory_usage=1024
    )
    mock_executor.execute_code.return_value = mock_result

    payload = {
        "code": "print('Hello World')",
        "language": "python",
        "test_cases": [{"input": "", "expected_output": "Hello World"}]
    }

    response = client.post("/api/execute", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure matches CodeExecutionResult schema
    assert data["status"] == "success"
    assert data["output"] == "Hello World"
    assert "error_message" in data
    assert "execution_time" in data

if __name__ == "__main__":
    # Manually run tests if executed as script
    try:
        test_health_check()
        print("✅ Health Check API passed")
        
        # Note: Running async tests manually is tricky without pytest-asyncio loop handling,
        # but TestClient handles async endpoints synchronously. 
        # The patching might be tricky if not running via pytest.
        # Let's try running via pytest in the terminal.
        pass
    except Exception as e:
        print(f"❌ Tests failed: {e}")
