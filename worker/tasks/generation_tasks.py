import time
import logging
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

logger = logging.getLogger(__name__)


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
def run_generation_job(job_id: int) -> dict | None:
    logger.info(f"[WORKER] Job {job_id} started")
    logger.info(f"[WORKER] mock_mode={settings.ai_mock_mode}")
    logger.info(f"[WORKER] kie_key={'present' if settings.kie_api_key else 'MISSING'}")
    
    db = SessionLocal()
    try:
        service = GenerationService(db)
        user_service = UserService(db)
        balance_service = BalanceService(db)

        job = service.get_job(job_id)
        
        logger.info(f"[Job {job_id}] Found: {job is not None}, status: {getattr(job, 'status', None)}")
        if not job or job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
            return {"job_id": job_id, "status": job.status if job else "not_found"}

        if getattr(settings, "ai_mock_mode", False):
            service.process_job(job.id)
            return {"job_id": job.id, "status": "mocked"}

        service.repo.update_job(job, status=JobStatus.PROCESSING)
        user = user_service.get_user_by_id(job.user_id)
        chat_id = user.telegram_user_id if user else None

        base_url = "https://api.kie.ai"
        api_key = settings.kie_api_key
        
        # --- API KEY VALIDATION ---
        if not api_key:
            logger.error("[KIE] KIE_API_KEY is empty!")
            service.repo.update_job(job, status=JobStatus.FAILED, error_message="KIE_API_KEY not set", completed=True)
            balance_service.add_credits(
                user_id=job.user_id,
                amount=job.credits_reserved,
                comment="Refund: KIE API key missing"
            )
            if chat_id and settings.bot_token:
                import asyncio
                asyncio.run(_notify_failed(chat_id, job.provider, job.prompt))
            raise ValueError("KIE_API_KEY not set")
            
        logger.info(f"[KIE] Using key: {api_key[:8]}...")
        # --------------------------
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Setup provider specific configs
        poll_url_template = f"{base_url}/v1/task/{{task_id}}" # default

        if job.provider == AIProvider.NANO_BANANA:
            url = f"{settings.kie_base_url}/v1/nano-banana/generate"
            width = job.job_payload.get("width", 1024)
            height = job.job_payload.get("height", 1024)
            payload = {
                "model": "nano-banana-pro",
                "prompt": job.prompt,
                "width": width,
                "height": height
            }
            if job.source_image_url:
                payload["image_url"] = job.source_image_url
            poll_interval = 5
            poll_timeout = 120
            is_video = False

        elif job.provider == AIProvider.VEO:
            url = f"{settings.kie_base_url}/v1/veo/generate"
            quality = job.job_payload.get("quality", "fast")
            payload = {
                "model": quality,  # As explicitly requested in payload example: "model": "fast" or "quality"
                "prompt": job.prompt,
                "duration": 8
            }
            if job.source_image_url:
                payload["image_url"] = job.source_image_url
            
            poll_url_template = f"{base_url}/v1/veo/query/{{task_id}}"
            poll_interval = 10
            poll_timeout = 300
            is_video = True

        elif job.provider == AIProvider.KLING:
            url = f"{settings.kie_base_url}/v1/kling/video/generate"
            mode = job.job_payload.get("mode", "std")
            duration = str(job.job_payload.get("duration", 5))
            payload = {
                "model_name": "kling-v3.0",
                "prompt": job.prompt,
                "duration": duration,
                "mode": mode
            }
            if job.source_image_url:
                payload["image_url"] = job.source_image_url
            
            poll_url_template = f"{base_url}/v1/kling/video/query/{{task_id}}"
            
            if duration == "15":
                poll_interval = 25
                poll_timeout = 900
            elif duration == "10":
                poll_interval = 20
                poll_timeout = 600
            else:
                poll_interval = 15
                poll_timeout = 300
                
            is_video = True
        else:
            service.repo.update_job(job, status=JobStatus.FAILED, error_message="Unknown provider", completed=True)
            return {"job_id": job_id, "status": "failed"}

        # 1. Start generation
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            logger.info(f"[KIE] Response status: {response.status_code}")
            logger.info(f"[KIE] Response body: {response.text[:200]}")
            
            response.raise_for_status()
            start_data = response.json()
            
            task_id = start_data.get("id") or (start_data.get("data") and start_data["data"].get("task_id"))
            if not task_id:
                raise ValueError(f"No task_id in response: {start_data}")
        except Exception as exc:
            logger.error(f"[WORKER] Job {job_id} FAILED: {exc}", exc_info=True)
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
            poll_url = poll_url_template.format(task_id=task_id)
            elapsed: int = 0
            final_result_url: str | None = None
            poll_timeout_int: int = int(poll_timeout)
            poll_interval_int: int = int(poll_interval)

            while elapsed < poll_timeout_int:
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
                    pass  # Ignore occasional network errors during polling

                time.sleep(poll_interval_int)
                elapsed += poll_interval_int

            # 3. Finalize
            bot_token = settings.bot_token
            if final_result_url:
                logger.info(f"[KIE] Task result: {final_result_url}")
                service.repo.update_job(
                    job,
                    status=JobStatus.COMPLETED,
                    external_job_id=str(task_id),
                    result_url=final_result_url,
                    completed=True
                )
                
                # Check achievements
                try:
                    from bot.services.achievements import check_and_award_achievements
                    newly_earned = check_and_award_achievements(
                        db=db,
                        user_id=job.user_id,
                        telegram_id=user.telegram_user_id,
                        lang=user.language_code or "ru"
                    )
                    db.commit()
                    
                    if newly_earned and chat_id and settings.bot_token:
                        asyncio.run(_notify_achievements(chat_id, settings.bot_token, newly_earned, user.language_code or "ru"))
                except Exception as ach_err:
                    logger.error(f"[Achievement] Worker error: {ach_err}")
                    
                if chat_id and bot_token and isinstance(final_result_url, str):
                    asyncio.run(_notify_success(chat_id, bot_token, job.provider, job.prompt, final_result_url, is_video))
                    logger.info(f"[WORKER] Job {job_id} completed, sent to user")
                return {"job_id": job.id, "status": "completed", "result_url": final_result_url}
            else:
                logger.error(f"[WORKER] Job {job_id} FAILED: Polling timeout or failure", exc_info=True)
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
            logger.error(f"[WORKER] Job {job_id} FAILED: {e}", exc_info=True)
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


async def _notify_achievements(chat_id: int, bot_token: str, achievements_with_bonus, lang: str):
    bot = Bot(token=bot_token)
    try:
        from shared.utils.i18n import I18n
        i18n = I18n()
        
        for ach, bonus in achievements_with_bonus:
            name = ach.name_uz if lang == "uz" else ach.name_ru
            text = (
                f"🏆 <b>Yangi yutuq!</b>\n\n{ach.emoji} <b>{name}</b>\n🎁 Bonus: <b>+{bonus}</b> kredit!"
                if lang == "uz" else
                f"🏆 <b>Новое достижение!</b>\n\n{ach.emoji} <b>{name}</b>\n🎁 Бонус: <b>+{bonus}</b> кредитов!"
            )
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    finally:
        await bot.session.close()


async def _notify_failed(chat_id: int, provider: str, prompt: str):
    bot_token = settings.bot_token
    if not bot_token:
        return
    bot = Bot(token=bot_token)
    try:
        text = f"❌ Ошибка генерации ({provider}).\nВаш промпт: <i>{prompt[:100]}...</i>\n\nКредиты возвращены на баланс."  # type: ignore
        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Failed to send failed notification to {chat_id}: {e}")
    finally:
        await bot.session.close()

@celery_app.task(name="worker.tasks.generation_tasks.cleanup_stale_jobs_task")
def cleanup_stale_jobs_task() -> None:
    """Periodic task to fail jobs pending > 30 min and notify users."""
    db = SessionLocal()
    try:
        service = GenerationService(db)
        balance_service = BalanceService(db)
        stale_jobs = service.cleanup_stale_jobs(minutes=30)
        
        if stale_jobs:
            logger.info(f"[Cleanup] Found {len(stale_jobs)} stale jobs")
            bot_token = settings.bot_token
            if bot_token:
                bot = Bot(token=bot_token)
                for job in stale_jobs:
                    # Notify user about failure and refund
                    user = service.user_service.repo.get_by_id(job.user_id)
                    if user:
                        lang = user.language_code
                        msg = (
                            "⚠️ Генерация не удалась. Кредиты возвращены на баланс."
                            if lang == "ru" else
                            "⚠️ Generatsiya muvaffaqiyatsiz. Kreditlar qaytarildi."
                        )
                        asyncio.run(bot.send_message(user.telegram_user_id, msg))
                # Note: Bot session should ideally be managed, but for infrequent task this is okay-ish
    except Exception as e:
        logger.error(f"[Cleanup] Error during stale jobs cleanup: {e}")
    finally:
        db.close()
