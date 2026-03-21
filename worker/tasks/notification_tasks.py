import logging
import asyncio
from datetime import datetime, timezone, timedelta
from celery import shared_task
from aiogram import Bot
from sqlalchemy import select

from bot.services.db_session import get_db_session
from backend.models.user import User
from backend.core.config import settings
from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)

@shared_task(name="daily_reminder_task")
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
        
        count = 0
        for user in users:
            try:
                lang = user.language_code or "ru"
                text = i18n.t(lang, "daily.reminder", streak=user.daily_streak)
                
                await bot.send_message(user.telegram_user_id, text)
                user.last_notification_at = now
                count += 1
                
                # Rate limiting for Telegram
                await asyncio.sleep(0.05)
                
            except Exception as e:
                logger.error(f"[Reminder] Failed to notify {user.telegram_user_id}: {e}")
        
        db.commit()
        logger.info(f"[Reminder] Sent to {count} users")
        
    finally:
        db.close()
        await bot.session.close()
@shared_task(name="lifecycle_notification_task")
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
                    
                except Exception as e:
                    logger.error(f"[Lifecycle] Day {day} failed for {user.telegram_user_id}: {e}")
            
            db.commit()
            
    finally:
        db.close()
        await bot.session.close()
