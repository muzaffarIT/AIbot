from backend.db.session import SessionLocal
from backend.services.generation_service import GenerationService
from worker.celery_app import celery_app


@celery_app.task(name="worker.tasks.generation_tasks.run_generation_job")
def run_generation_job(job_id: int) -> dict:
    db = SessionLocal()
    try:
        service = GenerationService(db)
        job = service.process_job(job_id)
        return {
            "job_id": job.id,
            "status": job.status,
            "result_url": job.result_url,
        }
    finally:
        db.close()
