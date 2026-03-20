"""
Smart notification scheduler using Celery Beat.
Sends targeted messages at Day 1, 3, 7, 30 after registration.
Rate limit: max 1 notification per 3 days per user.
"""
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot

logger = logging.getLogger(__name__)

NOTIFICATION_COOLDOWN_DAYS = 3


def _can_notify(user) -> bool:
    """Check if user can receive a notification (cooldown: 3 days)."""
    last = getattr(user, "last_notification_at", None)
    if not last:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - last).days >= NOTIFICATION_COOLDOWN_DAYS


async def send_notification(bot: Bot, telegram_id: int, text: str, db, user) -> bool:
    """Send notification and update last_notification_at. Returns True if sent."""
    if not _can_notify(user):
        return False
    try:
        await bot.send_message(telegram_id, text)
        user.last_notification_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"[Notification] Sent to user={telegram_id}")
        return True
    except Exception as e:
        logger.error(f"[Notification] Failed for user={telegram_id}: {e}")
        return False


async def run_scheduled_notifications(bot: Bot) -> None:
    """
    Run all lifecycle notifications.
    Should be called by Celery Beat daily.
    """
    from sqlalchemy import select
    from backend.db.session import SessionLocal
    from backend.models.user import User
    from backend.services.balance_service import BalanceService
    from backend.models.generation_job import GenerationJob
    from backend.models.credit_transaction import CreditTransaction
    from shared.enums.job_status import JobStatus

    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        users = db.execute(select(User)).scalars().all()

        for user in users:
            try:
                created = user.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)

                days_since = (now - created).days
                lang = user.language_code or "ru"
                tid = user.telegram_user_id
                balance_service = BalanceService(db)

                # Day 1 — if no generation yet
                if days_since == 1:
                    gen_count = db.execute(
                        select(GenerationJob).where(
                            GenerationJob.user_id == user.id,
                            GenerationJob.status == JobStatus.COMPLETED,
                        ).limit(1)
                    ).first()
                    if not gen_count:
                        tip = ("💡 Maslahat: botga inglizcha tavsif yozing — men rasm yarataman!"
                               if lang == "uz" else
                               "💡 Подсказка: напиши боту любое описание на английском — и я создам картинку!")
                        await send_notification(bot, tid, tip, db, user)

                # Day 3 — inactive reminder + 3 free credits
                elif days_since == 3:
                    if _can_notify(user):
                        balance_service.add_credits(user.id, 3, "activity_bonus")
                        msg = ("😢 Sog'indik! Sizga 3 ta bonus kredit berildi. Biror narsa yarating!"
                               if lang == "uz" else
                               "😢 Скучаем! Тебе начислено 3 бонусных кредита. Создай что-нибудь!")
                        await send_notification(bot, tid, msg, db, user)

                # Day 7 — upsell to purchase
                elif days_since == 7:
                    purchase_count = db.execute(
                        select(CreditTransaction).where(
                            CreditTransaction.user_id == user.id,
                            CreditTransaction.transaction_type == "telegram_stars_purchase",
                        ).limit(1)
                    ).first()
                    if not purchase_count:
                        msg = ("🎁 Maxsus taklif! Start paketi — 580⭐ evaziga 100 kredit"
                               if lang == "uz" else
                               "🎁 Специальное предложение! Start пакет — 100 кредитов всего за 580⭐")
                        await send_notification(bot, tid, msg, db, user)

                # Day 30 — loyalty reward
                elif days_since == 30:
                    purchase_count = db.execute(
                        select(CreditTransaction).where(
                            CreditTransaction.user_id == user.id,
                            CreditTransaction.transaction_type == "telegram_stars_purchase",
                        ).limit(1)
                    ).first()
                    if purchase_count:
                        balance_service.add_credits(user.id, 5, "loyalty_bonus")
                        msg = ("⭐ Biz bilan birga bo'lganingiz uchun rahmat! Sovg'a sifatida 5 kredit berildi 🎁"
                               if lang == "uz" else
                               "⭐ Спасибо что с нами! Тебе начислено 5 кредитов в подарок 🎁")
                        await send_notification(bot, tid, msg, db, user)

            except Exception as e:
                logger.error(f"[Notification] Error processing user={user.telegram_user_id}: {e}")
                continue

    finally:
        db.close()


async def send_daily_reminder_to_active_streakers(bot: Bot) -> None:
    """Send daily bonus reminder to users with streak > 0 who haven't claimed today."""
    from sqlalchemy import select
    from backend.db.session import SessionLocal
    from backend.models.user import User

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        users = db.execute(
            select(User).where(User.daily_streak > 0)
        ).scalars().all()

        for user in users:
            try:
                last_claim = getattr(user, "last_daily_claim", None)
                if last_claim:
                    if last_claim.tzinfo is None:
                        last_claim = last_claim.replace(tzinfo=timezone.utc)
                    if (now - last_claim).total_seconds() < 86400:
                        continue  # Already claimed today

                lang = user.language_code or "ru"
                streak = user.daily_streak or 0
                msg = (f"☀️ Kunlik bonusni olishni unutma!\n🔥 Streak: {streak} kun. Uzma!"
                       if lang == "uz" else
                       f"☀️ Не забудь получить ежедневный бонус!\n🔥 Твой стрик: {streak} дней. Не прерывай!")
                await send_notification(bot, user.telegram_user_id, msg, db, user)

            except Exception as e:
                logger.error(f"[DailyReminder] Error for user={user.telegram_user_id}: {e}")
    finally:
        db.close()
