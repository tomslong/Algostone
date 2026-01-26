"""代码执行接口测试."""
from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch
from app.models.schemas import CodeExecutionResult
from sandbox.executor import executor

client = TestClient(app)

def test_execute_code_success():
    """测试代码执行成功场景."""
    mock_result = CodeExecutionResult(
        status="success",
        output="Hello World\n",
        execution_time=0.01,
        memory_usage=1024
    )
    
    # Mock executor
    with patch("sandbox.executor.executor.execute_code", return_value=mock_result):
        response = client.post(
            "/api/execute",
            json={
                "code": "print('Hello World')",
                "language": "python"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["output"] == "Hello World\n"

def test_execute_code_empty():
    """测试空代码场景."""
    response = client.post(
        "/api/execute",
        json={
            "code": "   ",
            "language": "python"
        }
    )
    
    assert response.status_code == 400
    assert "Code cannot be empty" in response.json()["detail"]

def test_execute_code_error():
    """测试代码执行错误场景."""
    mock_result = CodeExecutionResult(
        status="error",
        error_type="SyntaxError",
        error_message="Syntax Error",
        execution_time=0.0
    )
    
    with patch("sandbox.executor.executor.execute_code", return_value=mock_result):
        response = client.post(
            "/api/execute",
            json={
                "code": "invalid code",
                "language": "python"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["error_type"] == "SyntaxError"

def test_unsupported_language():
    """测试不支持的语言."""
    # executor.execute_code 会返回 error 状态
    mock_result = CodeExecutionResult(
        status="error",
        error_type="UnsupportedLanguage",
        error_message="暂不支持 java 语言"
    )
    
    with patch("sandbox.executor.executor.execute_code", return_value=mock_result):
        response = client.post(
            "/api/execute",
            json={
                "code": "System.out.println('Hello');",
                "language": "java"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "暂不支持" in data["error_message"]


def test_execute_code_ignores_output_whitespace():
    result = executor.execute_code(
        code="print([0, 1])",
        test_cases=[{"expected_output": "[0,1]"}],
        language="python"
    )

    assert result.status == "success"
