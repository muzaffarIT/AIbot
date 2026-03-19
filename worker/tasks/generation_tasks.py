import requests

from backend.db.session import SessionLocal
from backend.services.generation_service import GenerationService
from backend.services.user_service import UserService
from backend.core.config import settings
from shared.enums.job_status import JobStatus
from shared.enums.providers import AIProvider
from worker.celery_app import celery_app


@celery_app.task(name="worker.tasks.generation_tasks.run_generation_job")
def run_generation_job(job_id: int) -> dict:
    db = SessionLocal()
    try:
        service = GenerationService(db)
        user_service = UserService(db)
        job = service.process_job(job_id)
        
        user = user_service.get_user_by_id(job.user_id)
        if user and settings.bot_token:
            chat_id = user.telegram_user_id
            
            if job.status == JobStatus.COMPLETED and job.result_url:
                is_video = job.provider in (AIProvider.KLING, AIProvider.VEO)
                text = f"✅ Ваша генерация ({job.provider}) готова!\nПромпт: {job.prompt}"
                
                method = "sendVideo" if is_video else "sendPhoto"
                payload = {
                    "chat_id": chat_id,
                    "caption": text
                }
                if is_video:
                    payload["video"] = job.result_url
                else:
                    payload["photo"] = job.result_url
                    
                requests.post(
                    f"https://api.telegram.org/bot{settings.bot_token}/{method}",
                    json=payload
                )
            elif job.status in (JobStatus.FAILED, JobStatus.CANCELLED):
                text = f"❌ Ошибка генерации ({job.provider}).\nКредиты были возвращены.\nПромпт: {job.prompt}"
                requests.post(
                    f"https://api.telegram.org/bot{settings.bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": text}
                )

        return {
            "job_id": job.id,
            "status": job.status,
            "result_url": job.result_url,
        }
    finally:
        db.close()
