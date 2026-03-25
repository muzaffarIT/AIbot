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


def poll_task(task_id, max_seconds=300, interval=5):
    elapsed = 0
    while elapsed < max_seconds:
        time.sleep(interval)
        elapsed += interval
        
        r = requests.get(
            f"{settings.kie_base_url}/api/v1/jobs/result/{task_id}",
            headers={"Authorization": f"Bearer {settings.kie_api_key}"}
        )
        logger.info(f"[KIE POLL] Full response: {r.text[:500]}")
        resp = r.json()

        # KIE.ai возвращает статус в data объекте
        task_data = resp.get("data", {})
        status = task_data.get("status", "")

        logger.info(f"[KIE POLL] taskId={task_id} status={status}")

        if status in ("success", "completed", "finish"):
            output = task_data.get("output", {})
            url = (output.get("imageUrl")
                   or output.get("image_url")
                   or output.get("videoUrl")
                   or output.get("video_url"))
            if url:
                logger.info(f"[KIE] Got result URL: {url[:80]}")
                return url
            logger.error(f"[KIE] Success but no URL in output: {output}")
            return None

        if status in ("failed", "error"):
            raise ValueError(f"KIE task failed: {resp}")

        # waiting/queuing/generating — продолжаем polling
        logger.info(f"[KIE POLL] status={status} elapsed={elapsed}s, continuing...")
    
    raise TimeoutError(f"KIE task {task_id} timeout")


async def send_result(telegram_id, result_url, provider, prompt, credits):
    if not settings.bot_token:
        logger.error("[NOTIFY] BOT_TOKEN is not set in worker!")
        return
    bot = Bot(token=settings.bot_token)
    try:
        caption = (
            f"✅ Готово!\n"
            f"🤖 {provider}\n"
            f"💬 {prompt[:100]}\n"
            f"💰 Потрачено: {credits} кредитов"
        )
        if provider in ["nano_banana", "nano-banana-pro", AIProvider.NANO_BANANA]:
            await bot.send_photo(
                chat_id=telegram_id,
                photo=result_url,
                caption=caption
            )
        else:
            await bot.send_video(
                chat_id=telegram_id,
                video=result_url,
                caption=caption
            )
        logger.info(f"[NOTIFY] Sent to {telegram_id}: {result_url[:50]}")
    except Exception as e:
        logger.error(f"[NOTIFY] Failed: {e}")
    finally:
        await bot.session.close()


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

        if not settings.kie_api_key:
            raise ValueError("KIE_API_KEY not set")
        logger.info(f"[KIE] Key: {settings.kie_api_key[:8]}...")
        
        headers = {
            "Authorization": f"Bearer {settings.kie_api_key}",
            "Content-Type": "application/json"
        }

        # Setup provider specific configs
        if job.provider == AIProvider.NANO_BANANA:
            url = f"{settings.kie_base_url}/api/v1/jobs/createTask"
            aspect_ratio = job.job_payload.get("aspect_ratio", "1:1")
            resolution = job.job_payload.get("resolution", "1K")
            payload = {
                "model": "nano-banana-pro",
                "input": {
                    "prompt": job.prompt,
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution,
                    "output_format": "png",
                    "image_input": [job.source_image_url] if job.source_image_url else []
                }
            }
            poll_interval = 5
            poll_timeout = 120

        elif job.provider == AIProvider.VEO:
            url = f"{settings.kie_base_url}/api/v1/jobs/createTask"
            quality = job.job_payload.get("quality", "fast")
            payload = {
                "model": "veo-3",
                "input": {
                    "prompt": job.prompt,
                    "duration": 8,
                    "resolution": "720p" if quality == "fast" else "1080p",
                    "image_input": [job.source_image_url] if job.source_image_url else []
                }
            }
            poll_interval = 10
            poll_timeout = 300

        elif job.provider == AIProvider.KLING:
            url = f"{settings.kie_base_url}/api/v1/jobs/createTask"
            mode = job.job_payload.get("mode", "std")
            duration = int(job.job_payload.get("duration", 5))
            payload = {
                "model": "kling-v3",
                "input": {
                    "prompt": job.prompt,
                    "duration": duration,
                    "mode": mode,
                    "image_input": [job.source_image_url] if job.source_image_url else []
                }
            }
            if duration == 15:
                poll_interval = 25
                poll_timeout = 900
            elif duration == 10:
                poll_interval = 20
                poll_timeout = 600
            else:
                poll_interval = 15
                poll_timeout = 300
        else:
            service.repo.update_job(job, status=JobStatus.FAILED, error_message="Unknown provider", completed=True)
            return {"job_id": job_id, "status": "failed"}

        # 1. Start generation
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        logger.info(f"[KIE] Response status: {response.status_code}")
        logger.info(f"[KIE] Response body: {response.text[:200]}")
        
        response.raise_for_status()
        start_data = response.json()
        
        data = start_data.get("data", {})
        task_id = (data.get("taskId")
                   or data.get("task_id")
                   or data.get("recordId"))
        if not task_id:
            raise ValueError(f"No taskId in KIE response: {start_data}")
        logger.info(f"[KIE] Task created: {task_id}")

        # 2. Polling
        final_result_url = poll_task(task_id, max_seconds=poll_timeout, interval=poll_interval)
        
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
                
            if chat_id:
                asyncio.run(send_result(
                    chat_id, final_result_url,
                    job.provider, job.prompt, job.credits_reserved
                ))
            return {"job_id": job.id, "status": "completed", "result_url": final_result_url}

    except Exception as e:
        logger.error(f"[JOB {job_id}] FAILED: {e}", exc_info=True)
        
        try:
            job.status = JobStatus.FAILED  # Used the enum directly here! Wait, the prompt used "failed", but enum might be safer.
            job.error_message = str(e)[:500]
            balance_service.add_credits(
                user_id=job.user_id,
                amount=job.credits_reserved,
                comment="Refund after crash"
            )
            db.commit()
            logger.info(f"[JOB {job_id}] Refunded {job.credits_reserved} credits")
        except Exception as db_err:
            logger.error(f"[JOB {job_id}] Refund failed: {db_err}")
        
        if 'user' in locals() and user:
            try:
                if settings.bot_token:
                    from aiogram import Bot
                    bot = Bot(token=settings.bot_token)
                    import asyncio
                    asyncio.run(bot.send_message(
                        chat_id=user.telegram_user_id,
                        text=f"⚠️ Генерация не удалась.\n"
                             f"✅ {job.credits_reserved} кредитов возвращено на баланс."
                    ))
                    asyncio.run(bot.session.close())
            except Exception as notify_err:
                logger.error(f"[JOB {job_id}] Notify failed: {notify_err}")

        return {"job_id": job_id, "status": "failed"}

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
                    user = service.user_service.repo.get_by_id(job.user_id)
                    if user:
                        lang = user.language_code
                        msg = (
                            "⚠️ Генерация не удалась. Кредиты возвращены на баланс."
                            if lang == "ru" else
                            "⚠️ Generatsiya muvaffaqiyatsiz. Kreditlar qaytarildi."
                        )
                        asyncio.run(bot.send_message(user.telegram_user_id, msg))
    except Exception as e:
        logger.error(f"[Cleanup] Error during stale jobs cleanup: {e}")
    finally:
        db.close()
