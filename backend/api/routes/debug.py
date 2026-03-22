from fastapi import APIRouter, Depends, HTTPException
import httpx
from backend.core.config import settings

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.get("/kie-ping")
async def kie_ping():
    import httpx
    from backend.core.config import settings
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{settings.kie_base_url}/v1/nano-banana/generate",
                headers={
                    "Authorization": f"Bearer {settings.kie_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": "a red circle",
                    "model": "nano-banana-pro",
                    "width": 512,
                    "height": 512
                }
            )
            return {
                "kie_status": r.status_code,
                "kie_body": r.json() if r.status_code == 200 else r.text,
                "key_first_8": settings.kie_api_key[:8] if settings.kie_api_key else "EMPTY",
                "base_url": settings.kie_base_url,
                "mock_mode": settings.ai_mock_mode
            }
    except Exception as e:
        return {"error": str(e)}
