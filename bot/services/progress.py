import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from backend.db.session import SessionLocal
from backend.models.generation_job import GenerationJob

logger = logging.getLogger(__name__)


async def track_generation_progress(bot: Bot, chat_id: int, message_id: int, job_id: int):
    """Edit the user's waiting message until the job reaches a terminal state.

    While processing → tick the timer every 30s ("⏳ ... 1 мин 30 сек").
    On FAILED → immediately replace the message with a clear error notice so
                the user is NOT left staring at a stale "in progress" line.
    On COMPLETED → replace with "✅ Готово!" (the actual result is sent as a
                   separate media message by the worker).
    On CANCELLED → mirror FAILED.
    """
    POLL_SEC = 5         # check DB every 5s for fast failure reflection
    TICK_TEXT_EVERY = 30  # only re-edit the timer text every 30s of elapsed

    elapsed = 0
    last_tick_edit = 0

    while True:
        await asyncio.sleep(POLL_SEC)
        elapsed += POLL_SEC

        db = SessionLocal()
        try:
            job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
        finally:
            db.close()

        if not job:
            return  # job was deleted — nothing to update

        status = str(job.status)

        if status in ("failed", "cancelled"):
            # Worker has already refunded credits + sent a separate failure
            # notification. Update the original "in progress" bubble so the
            # user doesn't think the task is still queued.
            err = (job.error_message or "").strip()
            short_err = (err[:200] + "…") if len(err) > 200 else err
            text = "❌ Генерация не удалась. Кредиты возвращены."
            if short_err:
                text += f"\n\n<i>{short_err}</i>"
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode="HTML",
                )
            except TelegramBadRequest:
                pass
            except Exception as e:
                logger.warning(f"[PROGRESS] failed-edit error: {e}")
            return

        if status == "completed":
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="✅ Готово! Результат отправлен отдельным сообщением.",
                )
            except TelegramBadRequest:
                pass
            except Exception as e:
                logger.warning(f"[PROGRESS] completed-edit error: {e}")
            return

        if status != "processing" and status != "pending":
            # Unknown terminal state — bail out without further edits.
            return

        # Only refresh the visible timer every TICK_TEXT_EVERY seconds
        # (avoids hammering the Telegram edit endpoint).
        if elapsed - last_tick_edit < TICK_TEXT_EVERY:
            continue
        last_tick_edit = elapsed

        try:
            mins = elapsed // 60
            secs = elapsed % 60
            time_str = f"{mins} мин {secs} сек" if mins > 0 else f"{secs} сек"
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"⏳ Ваша генерация в процессе... ({time_str})",
            )
        except TelegramBadRequest:
            # No-op edits raise this; ignore.
            pass
        except Exception as e:
            logger.debug(f"[PROGRESS] tick edit error: {e}")
