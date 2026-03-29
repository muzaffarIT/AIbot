from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services.generation_service import GenerationService

router = APIRouter()


class CreateJobRequest(BaseModel):
    telegram_user_id: int
    provider: str
    prompt: str
    source_image_url: str | None = None
    process_now: bool | None = None


def serialize_job(job) -> dict:
    return {
        "id": job.id,
        "user_id": job.user_id,
        "provider": job.provider,
        "prompt": job.prompt,
        "source_image_url": job.source_image_url,
        "status": job.status,
        "credits_reserved": job.credits_reserved,
        "external_job_id": job.external_job_id,
        "result_url": job.result_url,
        "result_payload": job.result_payload,
        "error_message": job.error_message,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }


@router.get("/telegram/{telegram_user_id}")
def get_user_jobs(
    telegram_user_id: int,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db)
) -> dict:
    try:
        service = GenerationService(db)
        jobs = service.get_user_jobs(telegram_user_id, limit=limit)
        return {
            "telegram_user_id": telegram_user_id,
            "jobs": [serialize_job(job) for job in jobs],
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        db.close()


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        service = GenerationService(db)
        job = service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return serialize_job(job)
    finally:
        db.close()


@router.post("/")
def create_job(payload: CreateJobRequest, db: Session = Depends(get_db)) -> dict:
    try:
        service = GenerationService(db)
        job = service.create_job_for_user(
            telegram_user_id=payload.telegram_user_id,
            provider=payload.provider,
            prompt=payload.prompt,
            source_image_url=payload.source_image_url,
            process_now=payload.process_now,
        )
        return serialize_job(job)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        db.close()
