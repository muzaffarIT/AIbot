import logging
import asyncio
from datetime import datetime, timezone, timedelta
from celery import shared_task
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import func, select

from bot.services.db_session import get_db_session
from backend.models.user import User
from backend.models.generation_job import GenerationJob
from backend.models.chat import ChatMessage
from backend.core.config import settings
from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)

@shared_task(name="worker.tasks.notification_tasks.daily_reminder_task")
def daily_reminder_task():
    """Sends daily bonus reminder to users who haven't claimed for > 24h."""
    asyncio.run(_send_daily_reminders())

async def _send_daily_reminders():
    bot = Bot(token=settings.bot_token)
    db = next(get_db_session())
    i18n = I18n()
    
    try:
        now = datetime.now(timezone.utc)
        # Users who claimed more than 24h ago OR never claimed
        # AND haven't been notified for > 24h
        stmt = select(User).where(
            (User.last_daily_claim == None) | (User.last_daily_claim < now - timedelta(hours=24)),
            (User.last_notification_at == None) | (User.last_notification_at < now - timedelta(hours=24))
        )
        users = db.execute(stmt).scalars().all()
        
        count: int = 0
        for user in users:
            try:
                lang = user.language_code or "ru"
                text = i18n.t(lang, "daily.reminder", streak=user.daily_streak)
                
                await bot.send_message(user.telegram_user_id, text)
                user.last_notification_at = now
                count = count + 1
                
                # Rate limiting for Telegram
                await asyncio.sleep(0.05)
                
            except TelegramForbiddenError:
                logger.warning(f"User blocked bot: {user.telegram_user_id}")
            except Exception as e:
                logger.error(f"[Reminder] Failed to notify {user.telegram_user_id}: {e}")
        
        db.commit()
        logger.info(f"[Reminder] Sent to {count} users")
        
    finally:
        db.close()
        await bot.session.close()
@shared_task(name="worker.tasks.notification_tasks.lifecycle_notification_task")
def lifecycle_notification_task():
    """Sends re-engagement messages on Day 1, 3, 7, 30 after registration."""
    asyncio.run(_send_lifecycle_notifications())


async def _send_lifecycle_notifications():
    bot = Bot(token=settings.bot_token)
    db = next(get_db_session())
    i18n = I18n()
    
    try:
        now = datetime.now(timezone.utc)
        
        # Lifecycle days: 1, 3, 7, 30
        for day in [1, 3, 7, 30]:
            target_date = now - timedelta(days=day)
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            stmt = select(User).where(
                User.created_at >= start_of_day,
                User.created_at <= end_of_day,
                (User.last_notification_at == None) | (User.last_notification_at < now - timedelta(days=3))
            )
            users = db.execute(stmt).scalars().all()
            
            for user in users:
                try:
                    # Check inactivity (last 48h)
                    from backend.models.generation_job import GenerationJob
                    recent_job = db.execute(
                        select(GenerationJob).where(
                            GenerationJob.user_id == user.id,
                            GenerationJob.created_at > now - timedelta(hours=48)
                        ).limit(1)
                    ).scalar()
                    
                    if recent_job:
                        continue # User is active
                    
                    lang = user.language_code or "ru"
                    text = i18n.t(lang, f"notification.lifecycle_day_{day}")
                    
                    await bot.send_message(user.telegram_user_id, text)
                    user.last_notification_at = now
                    await asyncio.sleep(0.05)
                    
                except TelegramForbiddenError:
                    logger.warning(f"[Lifecycle] User blocked bot: {user.telegram_user_id}")
                except Exception as e:
                    logger.error(f"[Lifecycle] Day {day} failed for {user.telegram_user_id}: {e}")
            
            db.commit()
            
    finally:
        db.close()
        await bot.session.close()


# ── Win-back: re-engage dormant users ────────────────────────────────────────
# Inactivity-based (unlike lifecycle_notification_task which is registration-day
# based). "Activity" = a generation job, a chat message, or a daily-bonus claim.
# A user gets at most one nudge per WINBACK_COOLDOWN_DAYS; the copy escalates
# with how long they've been gone (3 / 7 / 30 days).

WINBACK_MIN_INACTIVE_DAYS = 3
WINBACK_COOLDOWN_DAYS = 6
WINBACK_MAX_PER_RUN = 4000  # bound Telegram load per run

WINBACK_MESSAGES = {
    3: {
        "ru": "👋 Давно тебя не было! Загляни — покажу, что нового.\nО чём мечтаешь создать сегодня?",
        "uz": "👋 Ancha ko'rinmading! Kirib ko'r — nima yangilik borligini ko'rsataman.\nBugun nima yaratmoqchisan?",
    },
    7: {
        "ru": "Есть 2 минуты? Давай быстро разберём твою задачу.\nЧто нужно: текст, картинка или видео? Просто напиши — я помогу.",
        "uz": "2 daqiqa bormi? Keling, vazifangni tez hal qilamiz.\nNima kerak: matn, rasm yoki video? Yozgin — yordam beraman.",
    },
    30: {
        "ru": "Мы сильно обновились 🚀\nТеперь внутри — AI-чат с топовыми моделями и генерация фото/видео прямо в переписке.\nВернись и попробуй — первый результат за минуту.",
        "uz": "Biz katta yangilandik 🚀\nEndi ichida — eng zo'r modellar bilan AI-chat va suhbat ichida foto/video generatsiya.\nQaytib ko'r — birinchi natija bir daqiqada.",
    },
}


def _winback_tier(inactive_days: int) -> int | None:
    if inactive_days >= 30:
        return 30
    if inactive_days >= 7:
        return 7
    if inactive_days >= WINBACK_MIN_INACTIVE_DAYS:
        return 3
    return None


def _winback_keyboard(lang: str) -> InlineKeyboardMarkup | None:
    text = "✨ Открыть HARF AI" if lang != "uz" else "✨ HARF AI'ni ochish"
    url = (settings.miniapp_url or "").strip()
    if url.startswith("https://"):
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))]]
        )
    # Fall back to a menu callback the bot already handles
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data="start_menu")]]
    )


@shared_task(name="worker.tasks.notification_tasks.winback_inactive_task")
def winback_inactive_task():
    """Nudge users who have gone quiet, escalating copy by inactivity length."""
    asyncio.run(_send_winback())


async def _send_winback():
    bot = Bot(token=settings.bot_token)
    db = next(get_db_session())
    try:
        now = datetime.now(timezone.utc)
        cooldown_before = now - timedelta(days=WINBACK_COOLDOWN_DAYS)
        min_age_before = now - timedelta(days=WINBACK_MIN_INACTIVE_DAYS)

        # Candidates: old enough to be "inactive", not nudged recently.
        candidates = db.execute(
            select(User).where(
                User.created_at <= min_age_before,
                (User.last_notification_at == None) | (User.last_notification_at < cooldown_before),
            )
        ).scalars().all()

        if not candidates:
            logger.info("[Winback] no candidates")
            return

        # Precompute latest activity timestamps in two grouped queries.
        latest_job = dict(
            db.execute(
                select(GenerationJob.user_id, func.max(GenerationJob.created_at))
                .group_by(GenerationJob.user_id)
            ).all()
        )
        latest_chat = dict(
            db.execute(
                select(ChatMessage.user_id, func.max(ChatMessage.created_at))
                .group_by(ChatMessage.user_id)
            ).all()
        )

        i18n = I18n()  # reserved for future localized variants
        sent = 0
        for user in candidates:
            if sent >= WINBACK_MAX_PER_RUN:
                break

            # Most recent sign of life (ignore our own nudges).
            stamps = [user.created_at]
            if user.last_daily_claim:
                stamps.append(user.last_daily_claim)
            if latest_job.get(user.id):
                stamps.append(latest_job[user.id])
            if latest_chat.get(user.id):
                stamps.append(latest_chat[user.id])
            last_active = max(s for s in stamps if s is not None)

            inactive_days = (now - last_active).days
            tier = _winback_tier(inactive_days)
            if tier is None:
                continue

            lang = user.language_code or "ru"
            text = WINBACK_MESSAGES[tier].get(lang, WINBACK_MESSAGES[tier]["ru"])
            try:
                await bot.send_message(
                    user.telegram_user_id, text, reply_markup=_winback_keyboard(lang)
                )
                user.last_notification_at = now
                sent += 1
                await asyncio.sleep(0.04)  # ~25 msg/s
            except TelegramForbiddenError:
                # Blocked/deactivated — stop pestering; mark as notified so the
                # cooldown filter skips them next runs too.
                user.last_notification_at = now
            except TelegramRetryAfter as e:
                await asyncio.sleep(int(e.retry_after) + 1)
            except Exception as e:
                logger.error(f"[Winback] failed for {user.telegram_user_id}: {e}")

            if sent % 200 == 0:
                db.commit()

        db.commit()
        logger.info(f"[Winback] nudged {sent} dormant users")
    finally:
        db.close()
        await bot.session.close()
