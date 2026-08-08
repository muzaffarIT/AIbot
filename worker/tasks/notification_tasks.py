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


# ── Recipient hygiene ───────────────────────────────────────────────────────
# Centralise the "who can we message" predicate so every broadcast loop
# (bonus reminder, daily tip, lifecycle, win-back) honours opt-outs and
# stops pestering users who blocked the bot. Skipping blocked users is not
# just politeness — repeatedly hitting a blocked chat is what trips
# Telegram's flood/anti-spam limits.
def _broadcastable_users_query():
    """Return a SELECT for users we're allowed to market to."""
    return select(User).where(
        User.notifications_enabled == True,   # noqa: E712 — per-user opt-out
        User.is_blocked == False,             # noqa: E712 — hard bounces
    )


def _mark_blocked(db, user) -> None:
    """Record a hard delivery failure so we don't retry this user again."""
    user.is_blocked = True
    user.last_notification_at = datetime.now(timezone.utc)


@shared_task(name="worker.tasks.notification_tasks.daily_reminder_task")
def daily_reminder_task():
    """Morning nudge for users who haven't claimed today's bonus yet.

    Filter is calendar-day based (Tashkent local day, matching the bonus
    logic in UserService.claim_daily_bonus), NOT the old ">24h since last
    claim" window which fired for people who had already claimed today.
    """
    asyncio.run(_send_daily_reminders())


async def _send_daily_reminders():
    bot = Bot(token=settings.bot_token)
    db = get_db_session()
    i18n = I18n()

    try:
        # Tashkent local day — same tz the bonus itself uses.
        tashkent = timezone(timedelta(hours=5))
        now = datetime.now(tashkent)
        today = now.date()
        day_start = datetime.combine(today, datetime.min.time(), tzinfo=tashkent)

        # Eligible: opted-in, not blocked, AND did not claim today.
        # "Didn't claim today" = no claim OR claim was before local midnight.
        stmt = _broadcastable_users_query().where(
            (User.last_daily_claim == None) | (User.last_daily_claim < day_start)  # noqa: E711
        )
        users = db.execute(stmt).scalars().all()

        count = 0
        for user in users:
            try:
                lang = user.language_code or "ru"
                text = i18n.t(lang, "daily.reminder", streak=user.daily_streak)
                await bot.send_message(user.telegram_user_id, text)
                user.last_notification_at = now
                count += 1
                await asyncio.sleep(0.05)  # ~20 msg/s — under Telegram's limit
            except TelegramForbiddenError:
                _mark_blocked(db, user)
            except TelegramRetryAfter as e:
                await asyncio.sleep(int(e.retry_after) + 1)
            except Exception as e:
                logger.error(f"[Reminder] Failed to notify {user.telegram_user_id}: {e}")

        db.commit()
        logger.info(f"[Reminder] Sent to {count} users")
    finally:
        db.close()
        await bot.session.close()


# ── Daily educational / promo tip ───────────────────────────────────────────
# A "what's in it for me today" message that's NOT a generic reminder —
# concrete prompt ideas, model tips, and the odd upsell. Rotates by weekday
# (0=Mon … 6=Sun). This is the retention lever Syntx runs through its
# channel and Suzma through Instagram Reels; here it goes straight to the
# user in-bot. Two languages, same rotation index so A/B cohorts are aligned.

DAILY_TIPS = [
    # Monday
    {
        "ru": "🍌 <b>Понедельник — стартуем с картинки</b>\n\n"
              "Хороший промпт = детали. Слабо: «a cat».\n"
              "Сильно: <i>a fluffy cat on a windowsill, golden hour, cinematic, 8k</i>.\n\n"
              "Nano Banana · 1K — всего 10 кредитов. Попробуй 💡",
        "uz": "🍌 <b>Dushanba — rasmdan boshlaymiz</b>\n\n"
              "Yaxshi prompt = tafsilotlar. Zaif: «a cat».\n"
              "Kuchli: <i>a fluffy cat on a windowsill, golden hour, cinematic, 8k</i>.\n\n"
              "Nano Banana · 1K — atigi 10 kredit. Sinab ko'r 💡",
    },
    # Tuesday
    {
        "ru": "🎬 <b>Видео, которое залетает</b>\n\n"
              "Опиши <b>движение камеры</b>: <i>camera slowly zooms in, slow motion</i>.\n"
              "8 секунд — один яркий кадр. Veo 3 — от 30 кредитов.",
        "uz": "🎬 <b>Viral bo'ladigan video</b>\n\n"
              "<b>Kamera harakatini</b> tasvirla: <i>camera slowly zooms in, slow motion</i>.\n"
              "8 soniya — bitta yorqin kadrdan. Veo 3 — 30 kreditdan.",
    },
    # Wednesday
    {
        "ru": "🎥 <b>Kling силен в людях</b>\n\n"
              "Ходьба, танец, спорт — плавнее, чем у конкурентов.\n"
              "<i>a woman walking on a beach at sunset, slow motion</i> 🏖️",
        "uz": "🎥 <b>Kling — odamlar ustasi</b>\n\n"
              "Yurish, raqs, sport — raqiblardan tekisroq.\n"
              "<i>a woman walking on a beach at sunset, slow motion</i> 🏖️",
    },
    # Thursday
    {
        "ru": "💰 <b>Как экономить кредиты</b>\n\n"
              "1) Сначала дешёвое превью (Veo «быстрое» / Nano 1K).\n"
              "2) Понравилось → включай качество только для финала.\n"
              "3) Не забывай ежедневный бонус — до 10 кредитов в день бесплатно.",
        "uz": "💰 <b>Kreditlarni qanday tejash</b>\n\n"
              "1) Avval arzon preview (Veo «tez» / Nano 1K).\n"
              "2) Yoqdim → sifatni faqat yakuniy natija uchun yoq.\n"
              "3) Kunlik bonusni unutmama — kuniga 10 kreditgacha bepul.",
    },
    # Friday
    {
        "ru": "🔥 <b>Серия бонуса</b>\n\n"
              "Заходи каждый день — бонус растёт: 1→2→3...→10 кредитов.\n"
              "Пропустишь день — серия обнулится. Забери сегодня: кнопка <b>☀️ Бонус</b>.",
        "uz": "🔥 <b>Bonus seriyasi</b>\n\n"
              "Har kuni kir — bonus o'sadi: 1→2→3...→10 kredit.\n"
              "Kun o'tkazsang — seriya nolga tushadi. Bugun ol: <b>☀️ Bonus</b> tugmasi.",
    },
    # Saturday
    {
        "ru": "🧠 <b>Формула крутого промпта</b>\n\n"
              "<b>[объект] + [действие] + [среда] + [свет] + [стиль]</b>\n\n"
              "<i>a robot painting a wall, neon city, night, cinematic, 8k</i> 🤖🎨",
        "uz": "🧠 <b>Zo'r prompt formuli</b>\n\n"
              "<b>[obyekt] + [harakat] + [muhit] + [yorug'lik] + [uslub]</b>\n\n"
              "<i>a robot painting a wall, neon city, night, cinematic, 8k</i> 🤖🎨",
    },
    # Sunday
    {
        "ru": "🎁 <b>Воскресенье — время креатива + подарок</b>\n\n"
              "Сделай лучший ролик за выходные. Не хватает кредитов? "
              "Зови друга по своей ссылке — за каждого получишь бонус 👥",
        "uz": "🎁 <b>Yakshanba — ijod + sovg'a</b>\n\n"
              "Dam olish kunlarining eng zo'r videosini yasang. Kredit yetmayaptimi? "
              "Havola orqali do'st chaqir — har bir uchun bonus olasan 👥",
    },
]


@shared_task(name="worker.tasks.notification_tasks.daily_tip_task")
def daily_tip_task():
    """Send the rotating daily tip/promo to all eligible users."""
    asyncio.run(_send_daily_tip())


async def _send_daily_tip():
    bot = Bot(token=settings.bot_token)
    db = get_db_session()

    try:
        tashkent = timezone(timedelta(hours=5))
        now = datetime.now(tashkent)
        weekday = now.weekday()  # 0=Mon … 6=Sun
        tip = DAILY_TIPS[weekday % len(DAILY_TIPS)]

        users = db.execute(_broadcastable_users_query()).scalars().all()
        sent = 0
        for user in users:
            lang = user.language_code or "ru"
            text = tip.get(lang, tip["ru"])
            try:
                await bot.send_message(user.telegram_user_id, text, parse_mode="HTML")
                user.last_notification_at = now
                sent += 1
                await asyncio.sleep(0.04)  # ~25 msg/s
            except TelegramForbiddenError:
                _mark_blocked(db, user)
            except TelegramRetryAfter as e:
                await asyncio.sleep(int(e.retry_after) + 1)
            except Exception as e:
                logger.error(f"[DailyTip] failed for {user.telegram_user_id}: {e}")

            # Commit periodically so a crash mid-loop doesn't lose everything
            if sent % 200 == 0:
                db.commit()

        db.commit()
        logger.info(f"[DailyTip] weekday={weekday} sent={sent}")
    finally:
        db.close()
        await bot.session.close()


@shared_task(name="worker.tasks.notification_tasks.lifecycle_notification_task")
def lifecycle_notification_task():
    """Sends re-engagement messages on Day 1, 3, 7, 30 after registration."""
    asyncio.run(_send_lifecycle_notifications())


async def _send_lifecycle_notifications():
    bot = Bot(token=settings.bot_token)
    db = get_db_session()
    i18n = I18n()
    
    try:
        now = datetime.now(timezone.utc)
        
        # Lifecycle days: 1, 3, 7, 30
        for day in [1, 3, 7, 30]:
            target_date = now - timedelta(days=day)
            start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            stmt = _broadcastable_users_query().where(
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
                    _mark_blocked(db, user)
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
    db = get_db_session()
    try:
        now = datetime.now(timezone.utc)
        cooldown_before = now - timedelta(days=WINBACK_COOLDOWN_DAYS)
        min_age_before = now - timedelta(days=WINBACK_MIN_INACTIVE_DAYS)

        # Candidates: old enough to be "inactive", not nudged recently.
        # Respect opt-outs and skip blocked users (same predicate as other loops).
        candidates = db.execute(
            _broadcastable_users_query().where(
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
