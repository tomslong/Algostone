from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_get_settings_default():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["openai_api_key"] is None
    assert "model_name" in data
    assert "api_base" in data

def test_update_settings_returns_masked_key():
    payload = {
        "openai_api_key": "sk-new-key-12345",
        "model_name": "qwen-max",
        "api_base": "https://new-url.com"
    }

    response = client.post("/api/settings", json=payload)
    assert response.status_code == 200
    assert response.json()["openai_api_key"] == "*******"
    assert response.json()["model_name"] == "qwen-max"

def test_test_connection_success():
    with patch("app.api.routes.settings.httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        response = client.post("/api/settings/test-connection", json={
            "api_key": "sk-test",
            "model_name": "test-model"
        })
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"

def test_test_connection_failure():
    with patch("app.api.routes.settings.httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_post.return_value = mock_response
        
        response = client.post("/api/settings/test-connection", json={
            "api_key": "sk-invalid",
            "model_name": "test-model"
        })
        
        assert response.status_code == 200
        assert response.json()["status"] == "error"
        assert "Unauthorized" in response.json()["message"]
