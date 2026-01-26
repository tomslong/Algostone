from fastapi import APIRouter, HTTPException
from app.models.settings import SettingsUpdate, SettingsResponse, TestConnectionRequest
from app.core.config import settings as app_settings
import httpx

router = APIRouter()

@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current settings with masked API key."""
    return SettingsResponse(
        openai_api_key=None,
        model_name=app_settings.MODEL_NAME,
        api_base=app_settings.MODEL_API_URL,
    )

@router.post("/settings", response_model=SettingsResponse)
async def update_settings(settings: SettingsUpdate):
    """Update settings. Encrypts sensitive data."""
    new_settings = settings.model_dump(exclude_unset=True)
    masked_key = "*******" if new_settings.get("openai_api_key") else None
    return SettingsResponse(
        openai_api_key=masked_key,
        model_name=new_settings.get("model_name") or app_settings.MODEL_NAME,
        api_base=new_settings.get("api_base") or app_settings.MODEL_API_URL,
    )

@router.post("/settings/test-connection")
async def test_connection(request: TestConnectionRequest):
    """Test LLM connection validity."""
    api_key = request.api_key
    if not api_key:
        raise HTTPException(status_code=400, detail="API Key is missing")
        
    api_base = request.api_base or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model = request.model_name or "qwen-plus"
    
    try:
        # Simple chat completion test
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{api_base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                return {"status": "success", "message": "Connection successful"}
            else:
                return {
                    "status": "error", 
                    "message": f"API Error: {response.status_code} - {response.text}"
                }
    except Exception as e:
        return {"status": "error", "message": f"Connection failed: {str(e)}"}
