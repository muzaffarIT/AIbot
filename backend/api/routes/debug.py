from fastapi import APIRouter, Depends, HTTPException
import httpx
from backend.core.config import settings
from backend.db.session import SessionLocal
from backend.models.generation_job import GenerationJob
from backend.models.user import User
from backend.services.balance_service import BalanceService

router = APIRouter(prefix="/api/debug", tags=["debug"])

@router.post("/cleanup-stale")
async def cleanup_stale():
    db = SessionLocal()
    try:
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        stale = db.query(GenerationJob).filter(
            GenerationJob.status == "pending",
            GenerationJob.created_at < cutoff
        ).all()
        
        refunded = 0
        balance_service = BalanceService(db)
        for job in stale:
            job.status = "failed"
            job.error_message = "Manual cleanup"
            user = db.query(User).filter(User.id == job.user_id).first()
            if user:
                balance_service.add_credits(
                    user_id=user.id,
                    amount=job.credits_reserved,
                    comment="Manual cleanup"
                )
                refunded += job.credits_reserved
        db.commit()
        return {"cleaned": len(stale), "refunded": refunded}
    finally:
        db.close()

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
