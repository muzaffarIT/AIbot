"""
Debug endpoint for KIE.ai API diagnostics.
Only available when DEBUG=true in environment.
"""
import logging
from fastapi import APIRouter, HTTPException
import requests

from backend.core.config import settings

router = APIRouter(prefix="/api/debug", tags=["debug"])
logger = logging.getLogger(__name__)


@router.get("/kie-ping")
async def kie_ping():
    """
    Test request to KIE.ai API.
    Only available when DEBUG=true.
    Returns full response for diagnostics.
    """
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")

    api_key = settings.kie_api_key
    if not api_key:
        return {
            "error": "KIE_API_KEY is not set",
            "suggestion": "Set KIE_API_KEY in environment variables",
        }

    url = "https://api.kie.ai/v1/nano-banana/generate"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": "a simple red circle on white background",
        "model": "nano-banana-pro",
        "width": 512,
        "height": 512,
    }

    logger.info(f"[KIE-PING] POST {url}")
    logger.info(f"[KIE-PING] API key present: {bool(api_key)}, length={len(api_key)}")

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        logger.info(f"[KIE-PING] Status: {resp.status_code}")
        logger.info(f"[KIE-PING] Body: {resp.text[:500]}")

        try:
            body = resp.json()
        except Exception:
            body = {"raw": resp.text[:500]}

        return {
            "status_code": resp.status_code,
            "ok": resp.status_code < 300,
            "response": body,
            "api_key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "too_short",
            "url": url,
        }
    except requests.Timeout:
        logger.error("[KIE-PING] Request timed out")
        return {"error": "Request timed out after 30s", "url": url}
    except Exception as e:
        logger.error(f"[KIE-PING] Exception: {e}")
        return {"error": str(e), "url": url}


@router.get("/stale-jobs-cleanup")
async def cleanup_stale_jobs():
    """
    Mark pending jobs older than 1 hour as FAILED and refund credits.
    Only available when DEBUG=true.
    """
    if not settings.debug:
        raise HTTPException(status_code=404, detail="Not found")

    from backend.db.session import SessionLocal
    from sqlalchemy import select, text
    from backend.models.generation_job import GenerationJob
    from backend.services.balance_service import BalanceService
    from shared.enums.job_status import JobStatus

    db = SessionLocal()
    refunded = 0
    try:
        # Find jobs pending for more than 1 hour
        stale_result = db.execute(
            text("""
                SELECT id, user_id, credits_reserved FROM generation_jobs
                WHERE status = 'pending'
                AND created_at < NOW() - INTERVAL '1 hour'
            """)
        ).fetchall()

        balance_service = BalanceService(db)
        for row in stale_result:
            job_id, user_id, credits = row
            # Mark as failed
            db.execute(
                text("UPDATE generation_jobs SET status='failed', error_message='timeout' WHERE id=:id"),
                {"id": job_id}
            )
            # Refund credits
            if credits and credits > 0:
                balance_service.add_credits(user_id, credits, "timeout_refund")
                refunded += 1
                logger.info(f"[Cleanup] Refunded job_id={job_id} user_id={user_id} credits={credits}")

        db.commit()
        return {"cleaned_jobs": len(stale_result), "refunded": refunded}
    finally:
        db.close()
