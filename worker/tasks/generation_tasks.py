import time
import requests
import asyncio
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from backend.db.session import SessionLocal
from backend.services.generation_service import GenerationService
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from backend.core.config import settings
from shared.enums.job_status import JobStatus
from shared.enums.providers import AIProvider
from worker.celery_app import celery_app


def _do_post_request(url: str, headers: dict, json_data: dict, max_retries: int = 3) -> dict:
    delays = [5, 10, 20]
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, headers=headers, json=json_data, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "failed":
                raise ValueError("API returned failed status")
            return data
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])
            else:
                raise e
    raise ValueError("Max retries exceeded")


@celery_app.task(name="worker.tasks.generation_tasks.run_generation_job")
def run_generation_job(job_id: int) -> dict:
    print(">>> RUNNING TASK FOR JOB", job_id)
    db = SessionLocal()
    try:
        service = GenerationService(db)
        user_service = UserService(db)
        balance_service = BalanceService(db)
        
        job = service.get_job(job_id)
        print(">>> JOB FOUND?", job is not None)
        if not job or job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            print(">>> ABORTING TASK", job.status if job else "not_found")
            return {"job_id": job_id, "status": job.status if job else "not_found"}

        if getattr(settings, "ai_mock_mode", False):
            service.process_job(job.id)
            return {"job_id": job.id, "status": "mocked"}

        service.repo.update_job(job, status=JobStatus.PROCESSING)
        user = user_service.get_user_by_id(job.user_id)
        chat_id = user.telegram_user_id if user else None

        base_url = "https://api.kie.ai"
        api_key = settings.kie_api_key
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Setup provider specific configs
        if job.provider == AIProvider.NANO_BANANA:
            url = f"{base_url}/v1/nano-banana/generate"
            payload = {
                "prompt": job.prompt,
                "model": "nano-banana-pro",
                "width": 1024,
                "height": 1024
            }
            poll_interval = 5
            poll_timeout = 120
            is_video = False
        elif job.provider == AIProvider.VEO:
            url = f"{base_url}/v1/veo3/generate"
            payload = {
                "prompt": job.prompt,
                "model": "veo-3",
                "duration": 8,
                "quality": "fast"
            }
            poll_interval = 10
            poll_timeout = 300
            is_video = True
        elif job.provider == AIProvider.KLING:
            url = f"{base_url}/v1/kling/generate"
            payload = {
                "prompt": job.prompt,
                "model": "kling-v3",
                "duration": 5,
                "mode": "std"
            }
            poll_interval = 15
            poll_timeout = 600
            is_video = True
        else:
            service.repo.update_job(job, status=JobStatus.FAILED, error_message="Unknown provider", completed=True)
            return {"job_id": job_id, "status": "failed"}

        # 1. Start generation
        try:
            start_data = _do_post_request(url, headers, payload)
            # Depending on KIE API, they usually return a task_id
            task_id = start_data.get("id") or (start_data.get("data") and start_data["data"].get("task_id"))
            if not task_id:
                raise ValueError(f"No task_id in response: {start_data}")
        except Exception as exc:
            # Refund and Fail
            balance_service.add_credits(
                user_id=job.user_id,
                amount=job.credits_reserved,
                comment=f"Refund after start failed: {exc}"
            )
            service.repo.update_job(job, status=JobStatus.FAILED, error_message=str(exc), completed=True)
            if chat_id and settings.bot_token:
                asyncio.run(_notify_failed(chat_id, job.provider, job.prompt))
            return {"job_id": job.id, "status": "failed"}

        try:
            # 2. Polling
            poll_url = f"{base_url}/v1/task/{task_id}"
            elapsed = 0
            final_result_url = None
            
            while elapsed < poll_timeout:
                try:
                    resp = requests.get(poll_url, headers=headers, timeout=10)
                    resp.raise_for_status()
                    poll_data = resp.json()
                    status = poll_data.get("status")
                    
                    if status == "completed":
                        if is_video:
                            final_result_url = poll_data.get("data", {}).get("result", {}).get("video_url")
                        else:
                            final_result_url = poll_data.get("data", {}).get("result", {}).get("image_url")
                        break
                    elif status == "failed":
                        raise ValueError("Task failed during polling")
                        
                except Exception as e:
                    pass # Ignore occasional network errors during polling
                    
                time.sleep(poll_interval)
                elapsed += poll_interval

            # 3. Finalize
            bot_token = settings.bot_token
            if final_result_url:
                service.repo.update_job(
                    job,
                    status=JobStatus.COMPLETED,
                    external_job_id=str(task_id),
                    result_url=final_result_url,
                    completed=True
                )
                if chat_id and bot_token and isinstance(final_result_url, str):
                    asyncio.run(_notify_success(chat_id, bot_token, job.provider, job.prompt, final_result_url, is_video))
                return {"job_id": job.id, "status": "completed", "result_url": final_result_url}
            else:
                # Timeout or failed
                balance_service.add_credits(
                    user_id=job.user_id,
                    amount=job.credits_reserved,
                    comment="Refund after polling timeout/failure"
                )
                service.repo.update_job(job, status=JobStatus.FAILED, error_message="Polling timeout or failure", completed=True)
                if chat_id and bot_token:
                    asyncio.run(_notify_failed(chat_id, job.provider, job.prompt))
                return {"job_id": job.id, "status": "failed"}

        except Exception as e:
            print(f"CRITICAL ERROR IN WORKER: {e}")
            service.repo.update_job(job, status=JobStatus.FAILED, error_message=str(e), completed=True)
            return {"job_id": job.id, "status": "crashed"}

    finally:
        db.close()


async def _notify_success(chat_id: int, bot_token: str, provider: str, prompt: str, url: str, is_video: bool):
    bot = Bot(token=bot_token)
    try:
        text = f"✅ Ваша генерация ({provider}) готова!\nПромпт: {prompt}"
        
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Сгенерировать ещё", callback_data=f"gen_again:{provider}")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start_menu")]
            ]
        )
        
        if is_video:
            await bot.send_video(chat_id=chat_id, video=url, caption=text, reply_markup=markup)
        else:
            await bot.send_photo(chat_id=chat_id, photo=url, caption=text, reply_markup=markup)
    finally:
        await bot.session.close()


async def _notify_failed(chat_id: int, provider: str, prompt: str):
    bot_token = settings.bot_token
    if not bot_token:
        return
    bot = Bot(token=bot_token)
    try:
        text = f"❌ Ошибка генерации ({provider}).\nКредиты были возвращены.\nПромпт: {prompt}"
        await bot.send_message(chat_id=chat_id, text=text)
    finally:
        await bot.session.close()
