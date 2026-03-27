"""
Extended /admin dashboard — Block 12.
Only accessible to users listed in ADMIN_IDS env var.
"""
import os
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import func
from sqlalchemy.orm import Session

from bot.services.db_session import get_db_session
from backend.models.user import User
from backend.models.generation_job import GenerationJob
from backend.models.order import Order
from backend.core.config import settings

router = Router()

# Cost estimates per generation (in USD) — adjust as needed
COST_PER_IMAGE = 0.005   # Nano Banana (approx $0.005 per img)
COST_PER_VEO = 0.10      # Veo 3 (~$0.10 per video)
COST_PER_KLING = 0.15    # Kling (~$0.15 per video)

# Approximate server cost per day (Railway)
DAILY_SERVER_COST_USD = 0.50


def _get_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", settings.admin_ids)
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def _day_start(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _estimate_api_cost(db: Session, since: datetime) -> float:
    """Estimate KIE.ai API cost for completed jobs since `since`."""
    completed = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.status == "completed",
            GenerationJob.created_at >= since,
        )
        .all()
    )
    cost = 0.0
    for job in completed:
        if job.provider == "nano_banana":
            cost += COST_PER_IMAGE
        elif job.provider == "veo":
            cost += COST_PER_VEO
        elif job.provider == "kling":
            cost += COST_PER_KLING
        else:
            cost += COST_PER_IMAGE
    return cost


def _get_revenue(db: Session, since: datetime) -> float:
    """Sum of paid order amounts since `since`."""
    result = (
        db.query(func.coalesce(func.sum(Order.amount), 0.0))
        .filter(
            Order.status == "paid",
            Order.created_at >= since,
        )
        .scalar()
    )
    return float(result or 0.0)


@router.message(F.text == "/admin")
async def cmd_admin(message: Message) -> None:
    if message.from_user is None:
        return

    admin_ids = _get_admin_ids()
    if message.from_user.id not in admin_ids:
        return

    db: Session = get_db_session()
    try:
        now = datetime.now(timezone.utc)
        today_start = _day_start(now)
        month_start = _month_start(now)

        # ── Users ──────────────────────────────────────────────────────────
        total_users = db.query(User).count()
        new_today = db.query(User).filter(User.created_at >= today_start).count()

        # ── Referrals ──────────────────────────────────────────────────────
        total_referrals = (
            db.query(User)
            .filter(User.referred_by_telegram_id.isnot(None))
            .count()
        )

        # ── Active streaks ─────────────────────────────────────────────────
        yesterday = today_start - timedelta(days=1)
        active_streaks = (
            db.query(User)
            .filter(
                User.daily_streak > 0,
                User.last_daily_claim >= yesterday,
            )
            .count()
        )

        # ── Generations ────────────────────────────────────────────────────
        gens_today = (
            db.query(GenerationJob)
            .filter(GenerationJob.created_at >= today_start)
            .count()
        )
        gens_month = (
            db.query(GenerationJob)
            .filter(GenerationJob.created_at >= month_start)
            .count()
        )
        gens_failed_today = (
            db.query(GenerationJob)
            .filter(
                GenerationJob.status == "failed",
                GenerationJob.created_at >= today_start,
            )
            .count()
        )
        gens_pending = (
            db.query(GenerationJob)
            .filter(GenerationJob.status.in_(["pending", "processing"]))
            .count()
        )

        # ── Revenue ────────────────────────────────────────────────────────
        rev_today = _get_revenue(db, today_start)
        rev_month = _get_revenue(db, month_start)

        # ── API costs (estimates) ──────────────────────────────────────────
        api_today = _estimate_api_cost(db, today_start)
        api_month = _estimate_api_cost(db, month_start)

        # ── Profit ────────────────────────────────────────────────────────
        profit_today = rev_today - api_today - DAILY_SERVER_COST_USD
        profit_month = rev_month - api_month - (DAILY_SERVER_COST_USD * now.day)

        # ── Alert ─────────────────────────────────────────────────────────
        alert = ""
        if profit_today < 0:
            alert = (
                "\n⚠️ <b>Сегодня в минусе!</b>\n"
                f"API: ${api_today:.2f} | Выручка: ${rev_today:.2f}\n"
                "Проверь бесплатные генерации и конверсию!\n"
            )
        if gens_pending > 20:
            alert += f"\n🚨 <b>В очереди висит {gens_pending} задач!</b>\n"

        # ── Format ────────────────────────────────────────────────────────
        lines = [
            f"📊 <b>Отчёт HARF AI — {now.strftime('%d.%m.%Y %H:%M')} UTC</b>",
            "",
            "👥 <b>Пользователи</b>",
            f"  Всего: <b>{total_users}</b>",
            f"  Новых сегодня: <b>{new_today}</b>",
            f"  Рефералов всего: <b>{total_referrals}</b>",
            f"  Активных стриков: <b>{active_streaks}</b>",
            "",
            "⚡ <b>Генерации</b>",
            f"  Сегодня: <b>{gens_today}</b> (ошибок: {gens_failed_today})",
            f"  За месяц: <b>{gens_month}</b>",
            f"  В очереди: <b>{gens_pending}</b>",
            "",
            "💰 <b>Финансы (USD)</b>",
            f"  Выручка сегодня:   <b>${rev_today:.2f}</b>",
            f"  Выручка за месяц:  <b>${rev_month:.2f}</b>",
            f"  API расходы сегодня:  <b>${api_today:.2f}</b>",
            f"  API расходы за месяц: <b>${api_month:.2f}</b>",
            f"  Сервер за месяц:   <b>${DAILY_SERVER_COST_USD * now.day:.2f}</b>",
            "  ━━━━━━━━━━━━━━━",
            f"  Прибыль сегодня:   <b>${profit_today:.2f}</b>",
            f"  Прибыль за месяц:  <b>${profit_month:.2f}</b>",
        ]
        if alert:
            lines.append(alert)

        await message.answer("\n".join(lines), parse_mode="HTML")
    finally:
        db.close()
