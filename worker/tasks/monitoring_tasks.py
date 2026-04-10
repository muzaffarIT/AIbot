import asyncio
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from backend.db.session import SessionLocal
from backend.models.generation_job import GenerationJob
from backend.models.order import Order
from backend.services.settings_service import SettingsService
from backend.core.config import settings
from aiogram import Bot
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)

# Estimated API costs in USD
COST_MAP = {
    "nano_banana": 0.01,
    "veo": 0.15,
    "kling": 0.20,
}

@celery_app.task(name="worker.tasks.monitoring_tasks.financial_monitor_task")
def financial_monitor_task():
    asyncio.run(run_financial_monitor())

async def run_financial_monitor():
    db = SessionLocal()
    try:
        settings_service = SettingsService(db)
        three_days_ago = datetime.utcnow() - timedelta(days=3)

        # 1. Calculate API Cost (Estimate)
        jobs = db.query(GenerationJob).filter(
            GenerationJob.created_at >= three_days_ago,
            GenerationJob.status != "failed"
        ).all()
        
        sum_api = 0.0
        for job in jobs:
            sum_api += COST_MAP.get(job.provider, 0.05)

        # 2. Calculate Revenue
        orders = db.query(func.sum(Order.amount)).filter(
            Order.created_at >= three_days_ago,
            Order.status == "completed"
        ).scalar() or 0.0
        
        sum_rev = float(orders)

        logger.info(f"[MONITOR] 3-day stats: API Cost=${sum_api:.2f}, Revenue=${sum_rev:.2f}")

        # 3. Emergency Stop Logic
        if sum_api > (sum_rev * 2) and sum_api > 10.0:  # Also min threshold to avoid noise
            settings_service.set("welcome_credits", 5)
            settings_service.set("max_free_gens_per_day", 3)
            
            admin_msg = (
                f"🚨 <b>АВАРИЙНЫЙ РЕЖИМ!</b>\n\n"
                f"За последние 3 дня:\n"
                f"📉 Расходы API: <b>${sum_api:.2f}</b>\n"
                f"💰 Выручка: <b>${sum_rev:.2f}</b>\n\n"
                f"🛑 <b>Приняты меры:</b>\n"
                f"— Приветственные кредиты: <b>5</b>\n"
                f"— Лимит бесплатных ген/день: <b>3</b>\n\n"
                f"Проверьте систему!"
            )
            
            # Send to Admins
            bot = Bot(token=settings.bot_token)
            for admin_id in settings.admin_ids.split(","):
                if admin_id.strip():
                    try:
                        await bot.send_message(int(admin_id), admin_msg, parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Failed to notify admin {admin_id}: {e}")
            await bot.session.close()
            
            logger.critical(f"Emergency mode activated: api={sum_api}, rev={sum_rev}")

    finally:
        db.close()


# ─── Daily Sheets Summary ─────────────────────────────────────────────────────

@celery_app.task(name="worker.tasks.monitoring_tasks.daily_sheets_summary")
def daily_sheets_summary():
    """Write a daily summary row to the 📅 Дневник tab at 23:59 every day."""
    db = SessionLocal()
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_end = datetime.now(timezone.utc)

        # New users registered today
        from backend.models.user import User
        new_users = db.query(func.count(User.id)).filter(
            User.created_at >= today_start,
            User.created_at <= today_end,
        ).scalar() or 0

        # Generations today
        total_gens = db.query(func.count(GenerationJob.id)).filter(
            GenerationJob.created_at >= today_start,
            GenerationJob.created_at <= today_end,
        ).scalar() or 0

        ok_gens = db.query(func.count(GenerationJob.id)).filter(
            GenerationJob.created_at >= today_start,
            GenerationJob.created_at <= today_end,
            GenerationJob.status == "completed",
        ).scalar() or 0

        fail_gens = db.query(func.count(GenerationJob.id)).filter(
            GenerationJob.created_at >= today_start,
            GenerationJob.created_at <= today_end,
            GenerationJob.status == "failed",
        ).scalar() or 0

        # Payments confirmed today
        confirmed_payments = db.query(func.count(Order.id)).filter(
            Order.created_at >= today_start,
            Order.created_at <= today_end,
            Order.status == "completed",
        ).scalar() or 0

        # Revenue today (UZS)
        revenue_uzs = int(
            db.query(func.sum(Order.amount)).filter(
                Order.created_at >= today_start,
                Order.created_at <= today_end,
                Order.status == "completed",
            ).scalar() or 0
        )

        # Credits sold today (sum of credits in completed orders)
        credits_sold = 0
        try:
            from backend.models.credit_package import CreditPackage
            # Use a join or just approximate from orders
            orders_today = db.query(Order).filter(
                Order.created_at >= today_start,
                Order.created_at <= today_end,
                Order.status == "completed",
            ).all()
            for o in orders_today:
                credits_sold += getattr(o, "credits", 0) or 0
        except Exception:
            pass

        # API cost estimate
        jobs_today = db.query(GenerationJob).filter(
            GenerationJob.created_at >= today_start,
            GenerationJob.created_at <= today_end,
            GenerationJob.status == "completed",
        ).all()
        api_cost_usd = sum(COST_MAP.get(j.provider, 0.01) for j in jobs_today)

        # Write to sheets
        from backend.services.sheets_service import log_daily_summary
        log_daily_summary(
            new_users=new_users,
            total_gens=total_gens,
            ok_gens=ok_gens,
            fail_gens=fail_gens,
            confirmed_payments=confirmed_payments,
            revenue_uzs=revenue_uzs,
            credits_sold=credits_sold,
            api_cost_usd=api_cost_usd,
            errors=0,  # could hook into error counter later
        )
        logger.info(f"[DAILY SUMMARY] users={new_users} gens={total_gens} rev={revenue_uzs} api=${api_cost_usd:.3f}")

    except Exception as exc:
        logger.error(f"[DAILY SUMMARY] Failed: {exc}", exc_info=True)
    finally:
        db.close()
