from fastapi import APIRouter, Depends, HTTPException
import httpx
from backend.core.config import settings

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/kie-ping")
async def kie_ping():
    if not settings.debug:
        raise HTTPException(status_code=403, detail="Only available in DEBUG mode")
    
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.kie.ai/v1/nano-banana/generate",
            headers={"Authorization": f"Bearer {settings.kie_api_key}"},
            json={
                "prompt": "a red circle", 
                "model": "nano-banana-pro",
                "width": 512, 
                "height": 512
            }
        )
        return {
            "status": r.status_code, 
            "body": r.text[:500],
            "key_present": bool(settings.kie_api_key),
            "mock_mode": settings.ai_mock_mode
        }
