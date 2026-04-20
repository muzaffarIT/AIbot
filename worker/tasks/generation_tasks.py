import time
import logging
import json as json_lib
import requests
import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
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

def run_veo3_generation(prompt, quality, source_image_url,
                        kie_api_key, kie_base_url):
    """Veo 3 использует отдельный endpoint"""
    
    model = "veo3_fast" if quality == "fast" else "veo3_quality"
    
    payload = {
        "prompt": prompt,
        "model": model,
        "aspect_ratio": "16:9",
        "enableTranslation": True
    }
    
    if source_image_url:
        payload["generationType"] = "FIRST_AND_LAST_FRAMES_2_VIDEO"
        payload["imageUrls"] = [source_image_url]
    else:
        payload["generationType"] = "TEXT_2_VIDEO"
    
    headers = {
        "Authorization": f"Bearer {kie_api_key}",
        "Content-Type": "application/json"
    }
    
    url = f"{kie_base_url}/api/v1/veo/generate"
    logger.info(f"[VEO3] POST {url}")
    logger.info(f"[VEO3] payload: {json_lib.dumps(payload)[:300]}")
    
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    resp = r.json()
    logger.info(f"[VEO3] Response: {resp}")
    
    code = resp.get("code", 0)
    if code != 200:
        raise ValueError(f"VEO3 error {code}: {resp.get('msg')}")
    
    task_id = resp.get("data", {}).get("taskId")
    if not task_id:
        raise ValueError(f"VEO3: нет taskId: {resp}")
    
    logger.info(f"[VEO3] Task created: {task_id}")
    return task_id

def poll_veo3_task(task_id, kie_api_key, kie_base_url,
                  max_seconds=300, interval=5):
    """Polling для Veo 3 — отдельный endpoint с другой структурой"""
    
    elapsed = 0
    url = f"{kie_base_url}/api/v1/veo/record-info"
    headers = {"Authorization": f"Bearer {kie_api_key}"}
    
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
            resp = r.json()
            logger.info(f"[VEO3 POLL] {task_id} elapsed={elapsed}s")
            logger.info(f"[VEO3 POLL] body={r.text[:300]}")
            
            d = resp.get("data", {})
            flag = d.get("successFlag")
            # 0 = generating, 1 = success, 2 = failed, 3 = gen_failed
            
            logger.info(f"[VEO3 POLL] successFlag={flag}")
            
            if flag == 1:  # success!
                urls = d.get("response", {}).get("resultUrls", [])
                if urls:
                    logger.info(f"[VEO3] Result: {urls[0][:80]}")
                    return urls[0]
                logger.error(f"[VEO3] Success but no URL: {d}")
                return None
            
            if flag in (2, 3):  # failed
                raise ValueError(
                    f"VEO3 failed: {d.get('errorMessage', 'unknown')}"
                )
            
            # flag == 0 → ещё генерируется, продолжаем
            
        except requests.RequestException as e:
            logger.error(f"[VEO3 POLL] request error: {e}")
    
    raise TimeoutError(f"VEO3 task {task_id} timeout after {max_seconds}s")


async def _notify_user(telegram_id: int, url: str,
                       provider: str, prompt: str,
                       credits: int, bot_token: str):
    """Deliver generation result to user with robust fallback:
    1. Try sending as photo/video by direct URL (fastest path)
    2. If Telegram rejects the URL, download bytes and upload as file
    3. If all else fails, send the URL as a plain text message so user still gets it.
    """
    if not bot_token:
        logger.error("[NOTIFY] BOT_TOKEN не задан!")
        return
    from aiogram import Bot
    from aiogram.types import (
        InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
    )
    from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

    # Normalize provider to string value (accept enum / enum-like / str)
    provider_str = getattr(provider, "value", None) or str(provider or "").lower()

    bot = Bot(token=bot_token)
    try:
        caption = (
            f"✅ Готово!\n"
            f"💬 {prompt[:100]}\n"
            f"💰 Потрачено: {credits} кр."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="🔄 Ещё раз",
                callback_data=f"gen_again:{provider_str}"
            ),
            InlineKeyboardButton(
                text="🏠 Меню",
                callback_data="start_menu"
            )
        ]])
        is_video = any(
            token in provider_str
            for token in ("veo", "kling")
        )
        logger.info(
            f"[NOTIFY] telegram_id={telegram_id} provider={provider_str} "
            f"is_video={is_video} url={url[:120]}"
        )

        async def _send_by_url():
            if is_video:
                await bot.send_video(
                    chat_id=telegram_id, video=url,
                    caption=caption, reply_markup=kb,
                )
            else:
                await bot.send_photo(
                    chat_id=telegram_id, photo=url,
                    caption=caption, reply_markup=kb,
                )

        # Download file once — reused by both upload and document paths
        _file_bytes: bytes | None = None

        async def _fetch_bytes() -> bytes:
            nonlocal _file_bytes
            if _file_bytes is None:
                import requests as _rq
                r = _rq.get(url, timeout=120)
                r.raise_for_status()
                _file_bytes = r.content
                logger.info(f"[NOTIFY] fetched {len(_file_bytes)} bytes")
            return _file_bytes

        async def _send_by_upload():
            # Try send_photo/send_video with uploaded bytes
            # (Telegram photo limit ≈10 MB upload; bigger files will 400)
            data = await _fetch_bytes()
            ext = ".mp4" if is_video else ".png"
            file = BufferedInputFile(data, filename=f"result{ext}")
            if is_video:
                await bot.send_video(
                    chat_id=telegram_id, video=file,
                    caption=caption, reply_markup=kb,
                )
            else:
                await bot.send_photo(
                    chat_id=telegram_id, photo=file,
                    caption=caption, reply_markup=kb,
                )

        async def _send_as_document():
            # Bigger size budget (~50 MB). Keeps FULL original quality
            # — perfect for 4K PNGs that blow past the send_photo limit.
            data = await _fetch_bytes()
            ext = ".mp4" if is_video else ".png"
            file = BufferedInputFile(data, filename=f"HARF_result{ext}")
            await bot.send_document(
                chat_id=telegram_id,
                document=file,
                caption=caption,
                reply_markup=kb,
            )

        async def _send_as_text():
            # Absolute last resort — user must see SOMETHING
            await bot.send_message(
                chat_id=telegram_id,
                text=f"{caption}\n\n🔗 {url}",
                reply_markup=kb,
                disable_web_page_preview=False,
            )

        async def _try_fallback_chain(reason: str):
            logger.warning(f"[NOTIFY] by_url failed ({reason}) — trying upload…")
            try:
                await _send_by_upload()
                logger.info(f"[NOTIFY] ✅ by_upload {telegram_id}")
                return
            except Exception as e2:
                logger.warning(
                    f"[NOTIFY] by_upload failed ({e2}) — trying document…"
                )
            try:
                await _send_as_document()
                logger.info(f"[NOTIFY] ✅ as_document {telegram_id}")
                return
            except Exception as e3:
                logger.error(
                    f"[NOTIFY] as_document failed ({e3}) — falling back to text"
                )
            try:
                await _send_as_text()
                logger.info(f"[NOTIFY] ✅ as_text {telegram_id}")
            except Exception as e4:
                logger.error(f"[NOTIFY] ALL paths failed: {e4}")

        try:
            await _send_by_url()
            logger.info(f"[NOTIFY] ✅ by_url {telegram_id}")
        except TelegramBadRequest as e:
            await _try_fallback_chain(str(e))
        except Exception as e:
            await _try_fallback_chain(str(e))
    except TelegramForbiddenError:
        logger.warning(f"[NOTIFY] {telegram_id} заблокировал бота")
    except Exception as e:
        logger.error(f"[NOTIFY] Unexpected: {e}", exc_info=True)
    finally:
        await bot.session.close()


@celery_app.task(
    name="worker.tasks.generation_tasks.run_generation_job",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def run_generation_job(self, job_id: int) -> dict | None:
    logger.info(f"[WORKER] Job {job_id} started")
    logger.info(f"[WORKER] mock_mode={settings.ai_mock_mode}")
    logger.info(f"[WORKER] kie_key={'present' if settings.kie_api_key else 'MISSING'}")
    _job_start_time = time.time()

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

        # ── Sheets: log generation started ──────────────────────────────────
        try:
            from backend.services.sheets_service import log_generation_started
            log_generation_started(
                job_id=job.id,
                telegram_id=user.telegram_user_id if user else 0,
                full_name=user.first_name or "—" if user else "—",
                username=user.username if user else None,
                provider=job.provider,
                prompt=job.prompt or "",
                credits=job.credits_reserved,
            )
        except Exception as _se:
            logger.error(f"[SHEETS] log_generation_started failed: {_se}")

        if not settings.kie_api_key:
            raise ValueError("KIE_API_KEY not set")
        logger.info(f"[KIE] Key: {settings.kie_api_key[:8]}...")
        
        headers = {
            "Authorization": f"Bearer {settings.kie_api_key}",
            "Content-Type": "application/json"
        }

        # Setup provider specific configs
        if job.provider == AIProvider.VEO:
            task_id = run_veo3_generation(
                prompt=job.prompt,
                quality=job.job_payload.get("quality", "fast"),
                source_image_url=job.source_image_url,
                kie_api_key=settings.kie_api_key,
                kie_base_url=settings.kie_base_url
            )
            final_result_url = poll_veo3_task(
                task_id=task_id,
                kie_api_key=settings.kie_api_key,
                kie_base_url=settings.kie_base_url
            )
        else:
            if job.provider == AIProvider.NANO_BANANA:
                url = f"{settings.kie_base_url}/api/v1/jobs/createTask"
                # job_payload comes from bot/keyboards/quality_menu.QUALITY_DATA:
                #   image_size       → aspect_ratio ("1:1")
                #   image_resolution → resolution ("2K" / "4K"), only for nano-banana-2
                #   _nano_model      → kie.ai model name ("nano-banana" / "nano-banana-2")
                jp = job.job_payload or {}
                aspect_ratio = jp.get("image_size") or jp.get("aspect_ratio") or "1:1"
                resolution = jp.get("image_resolution") or jp.get("resolution") or "1K"
                nano_model = jp.get("_nano_model") or "nano-banana"
                # Edit mode (source image) requires the edit model
                if job.source_image_url:
                    nano_model = "nano-banana-edit"
                # kie.ai model-ID rules (verified via docs.kie.ai):
                #   google/nano-banana        → v1 text-to-image, 1K only (aspect_ratio via image_size)
                #   google/nano-banana-edit   → v1 image-to-image edit
                #   nano-banana-pro           → NO prefix; supports resolution 1K/2K/4K
                #   nano-banana-2             → NO prefix; supports resolution 1K/2K/4K
                base = nano_model.split("/", 1)[-1]  # strip any "google/" the caller added
                if base in ("nano-banana", "nano-banana-edit"):
                    api_model = f"google/{base}"
                    # v1 uses image_size for aspect ratio; no resolution knob
                    input_block = {
                        "prompt": job.prompt,
                        "image_size": aspect_ratio,
                        "output_format": "png",
                        "image_input": [job.source_image_url] if job.source_image_url else [],
                    }
                else:
                    # nano-banana-pro / nano-banana-2
                    api_model = base
                    input_block = {
                        "prompt": job.prompt,
                        "aspect_ratio": aspect_ratio,
                        "resolution": resolution,
                        "output_format": "png",
                        "image_input": [job.source_image_url] if job.source_image_url else [],
                    }
                payload = {
                    "model": api_model,
                    "input": input_block,
                }
                poll_interval = 5
                poll_timeout = 120

            elif job.provider == AIProvider.KLING:
                url = f"{settings.kie_base_url}/api/v1/jobs/createTask"
                mode = job.job_payload.get("mode", "std")
                duration = int(job.job_payload.get("duration", 5))
                payload = {
                    "model": "kling-3.0/video",
                    "input": {
                        "prompt": job.prompt,
                        "duration": str(duration),
                        "mode": mode,
                        "aspect_ratio": "16:9",
                        "sound": False,
                        "image_urls": [job.source_image_url] if job.source_image_url else []
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
            logger.info(f"[KIE] Sending payload: {json_lib.dumps(payload)[:500]}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            logger.info(f"[KIE] Response status: {response.status_code}")
            logger.info(f"[KIE] Response body: {response.text[:200]}")
            
            response.raise_for_status()
            resp = response.json()
            
            code = resp.get("code", 0)
            msg = resp.get("msg", "")

            if code == 402:
                raise ValueError(f"KIE: недостаточно кредитов: {msg}")
            if code == 401:
                raise ValueError(f"KIE: неверный ключ: {msg}")
            if code == 422:
                raise ValueError(f"KIE: неверная модель: {msg}")
            if code != 200:
                raise ValueError(f"KIE error {code}: {msg}")

            data = resp.get("data") or {}
            task_id = (data.get("taskId")
                       or data.get("task_id")
                       or data.get("recordId"))
            if not task_id:
                raise ValueError(f"Нет taskId в ответе: {resp}")
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

            # ── Sheets: log generation complete ─────────────────────────────
            try:
                from backend.services.sheets_service import log_generation_complete
                _elapsed = int(time.time() - _job_start_time)
                log_generation_complete(
                    job_id=job.id,
                    telegram_id=user.telegram_user_id if user else 0,
                    full_name=user.first_name or "—" if user else "—",
                    username=user.username if user else None,
                    provider=job.provider,
                    prompt=job.prompt or "",
                    credits=job.credits_reserved,
                    elapsed_seconds=_elapsed,
                )
            except Exception as _se:
                logger.error(f"[SHEETS] log_generation_complete failed: {_se}")

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
                    loop.run_until_complete(_notify_user(
                        chat_id,
                        final_result_url,
                        job.provider,
                        job.prompt,
                        job.credits_reserved,
                        settings.bot_token
                    ))
                finally:
                    loop.close()
            return {"job_id": job.id, "status": "completed", "result_url": final_result_url}

    except Exception as e:
        logger.error(f"[JOB {job_id}] FAILED: {e}", exc_info=True)

        # ── Sheets: log generation failed ───────────────────────────────────
        try:
            from backend.services.sheets_service import log_generation_failed
            _u = locals().get("user")
            log_generation_failed(
                job_id=job_id,
                telegram_id=_u.telegram_user_id if _u else 0,
                full_name=_u.first_name or "—" if _u else "—",
                username=_u.username if _u else None,
                provider=getattr(locals().get("job"), "provider", "unknown"),
                prompt=getattr(locals().get("job"), "prompt", "") or "",
                credits=getattr(locals().get("job"), "credits_reserved", 0),
                error=str(e),
            )
        except Exception as _se:
            logger.error(f"[SHEETS] log_generation_failed failed: {_se}")

        try:
            job.status = JobStatus.FAILED
            job.error_message = str(e)[:500]
            # Idempotency: only refund if not already refunded
            from backend.models.credit_transaction import CreditTransaction
            from shared.enums.credit_transaction_type import CreditTransactionType
            already_refunded = db.query(CreditTransaction).filter(
                CreditTransaction.reference_type == "generation_job",
                CreditTransaction.reference_id == str(job_id),
                CreditTransaction.transaction_type == CreditTransactionType.REFUND,
            ).first()
            if not already_refunded:
                balance_service.add_credits(
                    user_id=job.user_id,
                    amount=job.credits_reserved,
                    transaction_type=CreditTransactionType.REFUND,
                    reference_type="generation_job",
                    reference_id=str(job_id),
                    comment="Refund after crash",
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
            except TelegramForbiddenError:
                logger.warning(f"[JOB {job_id}] User {user.telegram_user_id} blocked bot")
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
    except TelegramForbiddenError:
        logger.warning(f"[NOTIFY_SUCCESS] User {chat_id} blocked the bot")
    except Exception as e:
        logger.error(f"[NOTIFY_SUCCESS] Failed: {e}")
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
    except TelegramForbiddenError:
        logger.warning(f"[NOTIFY_ACHVS] User {chat_id} blocked the bot")
    except Exception as e:
        logger.error(f"[NOTIFY_ACHVS] Failed: {e}")
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
    except TelegramForbiddenError:
        logger.warning(f"[NOTIFY_FAILED] User {chat_id} blocked the bot")
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
                        loop = asyncio.new_event_loop()
                        try:
                            loop.run_until_complete(bot.send_message(user.telegram_user_id, msg))
                        finally:
                            loop.close()
    except TelegramForbiddenError:
        pass
    except Exception as e:
        logger.error(f"[Cleanup] Error during stale jobs cleanup: {e}")
    finally:
        db.close()
