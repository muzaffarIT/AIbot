import time
import logging
import json as json_lib
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


def poll_task(task_id: str, max_seconds: int = 300,
              interval: int = 5) -> str | None:
    elapsed = 0
    url = f"{settings.kie_base_url}/api/v1/jobs/recordInfo"
    headers = {"Authorization": f"Bearer {settings.kie_api_key}"}

    while elapsed < max_seconds:
        time.sleep(interval)
        elapsed += interval

        try:
            r = requests.get(
                url,
                params={"taskId": task_id},
                headers=headers,
                timeout=30
            )
            logger.info(
                f"[KIE POLL] taskId={task_id} "
                f"status={r.status_code} "
                f"elapsed={elapsed}s"
            )
            logger.info(f"[KIE POLL] body={r.text[:300]}")

            if r.status_code != 200:
                logger.warning(f"[KIE POLL] Non-200: {r.status_code}")
                continue

            resp = r.json()
            task_data = resp.get("data", {})

            # ВАЖНО: поле называется "state", не "status"!
            state = task_data.get("state", "")
            logger.info(f"[KIE POLL] state={state}")

            if state == "success":
                # resultJson — это строка JSON, парсим её
                result_json_str = task_data.get("resultJson", "")
                try:
                    result_json = json_lib.loads(result_json_str)
                    urls = result_json.get("resultUrls", [])
                    if urls:
                        logger.info(f"[KIE] Result: {urls[0]}")
                        return urls[0]
                except Exception as parse_err:
                    logger.error(
                        f"[KIE] Parse error: {parse_err}, "
                        f"raw={result_json_str[:200]}"
                    )
                # Если resultUrls пустой — ищем в других полях
                logger.warning(f"[KIE] Success but no URL: {task_data}")
                return None

            if state == "fail":
                fail_msg = task_data.get("failMsg", "unknown")
                raise ValueError(f"KIE task failed: {fail_msg}")

        except requests.RequestException as req_err:
            logger.error(f"[KIE POLL] Request error: {req_err}")

    raise TimeoutError(
        f"KIE task {task_id} timeout after {max_seconds}s"
    )



async def _notify(telegram_id, url, provider, prompt, credits):
    if not settings.bot_token:
        logger.error("[NOTIFY] BOT_TOKEN is not set in worker!")
        return
    bot = Bot(token=settings.bot_token)
    try:
        caption = (
            f"✅ Готово!\n"
            f"💬 {prompt[:100]}\n"
            f"💰 Потрачено: {credits} кр."
        )
        if provider in ("nano_banana", "nano-banana-pro", AIProvider.NANO_BANANA):
            await bot.send_photo(
                chat_id=telegram_id,
                photo=url,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🔄 Ещё раз",
                        callback_data=f"gen_again:{provider}"
                    ),
                    InlineKeyboardButton(
                        text="🏠 Меню",
                        callback_data="start_menu"
                    )
                ]])
            )
        else:
            await bot.send_video(
                chat_id=telegram_id,
                video=url,
                caption=caption
            )
        logger.info(f"[NOTIFY] Sent to {telegram_id} ✅")
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
        resp = response.json()
        
        code = resp.get("code", 0)
        msg = resp.get("msg", "")

        if code == 402:
            raise ValueError(f"KIE: недостаточно кредитов. {msg}")
        if code == 401:
            raise ValueError(f"KIE: неверный API ключ. {msg}")
        if code != 200:
            raise ValueError(f"KIE error {code}: {msg}")

        data = resp.get("data") or {}
        task_id = (data.get("taskId")
                   or data.get("task_id")
                   or data.get("recordId"))
        if not task_id:
            raise ValueError(f"Нет taskId: {resp}")
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
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(_notify_achievements(chat_id, settings.bot_token, newly_earned, user.language_code or "ru"))
                    finally:
                        loop.close()
            except Exception as ach_err:
                logger.error(f"[Achievement] Worker error: {ach_err}")
                
            if chat_id:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_notify(
                        chat_id,
                        final_result_url,
                        job.provider,
                        job.prompt,
                        job.credits_reserved
                    ))
                finally:
                    loop.close()
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
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(bot.send_message(
                            chat_id=user.telegram_user_id,
                            text=f"⚠️ Генерация не удалась.\n"
                                 f"✅ {job.credits_reserved} кредитов возвращено на баланс."
                        ))
                        loop.run_until_complete(bot.session.close())
                    finally:
                        loop.close()
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
