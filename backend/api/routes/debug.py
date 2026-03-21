from fastapi import APIRouter, Depends, HTTPException
import requests
from backend.core.config import settings

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/kie-ping")
async def kie_ping():
    if not settings.debug:
        raise HTTPException(status_code=403, detail="Only available in DEBUG mode")
    
    url = f"{settings.kie_base_url}/v1/nano-banana/generate"
    headers = {"Authorization": f"Bearer {settings.kie_api_key}"}
    payload = {
        "model": "nano-banana-pro",
        "prompt": "a red circle",
        "width": 1024,
        "height": 1024
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        return {
            "status_code": resp.status_code,
            "response": resp.json() if resp.status_code == 200 else resp.text,
            "settings": {
                "ai_mock_mode": settings.ai_mock_mode,
                "kie_base_url": settings.kie_base_url,
                "kie_api_key_present": bool(settings.kie_api_key)
            }
        }
    except Exception as e:
        return {"error": str(e)}
