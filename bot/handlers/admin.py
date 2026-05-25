"""
Extended /admin dashboard — Block 12.
Only accessible to users listed in ADMIN_IDS env var.
"""
import logging
import os
from datetime import datetime, timedelta, timezone

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func
from sqlalchemy.orm import Session

from bot.services.db_session import get_db_session
from backend.models.user import User
from backend.models.generation_job import GenerationJob
from backend.models.order import Order
from backend.models.credit_transaction import CreditTransaction
from backend.services.balance_service import BalanceService
from shared.enums.credit_transaction_type import CreditTransactionType
from shared.enums.job_status import JobStatus
from backend.core.config import settings

logger = logging.getLogger(__name__)

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
            "",
            "🛠 <b>Админ-команды</b>",
            "  /broadcast — рассылка всем",
            "  /broadcast_ru — только русскоязычным",
            "  /broadcast_uz — только узбекоязычным",
            "  /reset_queue — обнулить очередь (всем юзерам refund)",
        ]
        if alert:
            lines.append(alert)

        await message.answer("\n".join(lines), parse_mode="HTML")
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# /reset_queue — mark all stuck pending/processing jobs as FAILED + refund.
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("reset_queue"))
async def cmd_reset_queue(message: Message, bot: Bot) -> None:
    """Reset the global generation queue.

    Marks every job in PENDING or PROCESSING status as FAILED, refunds the
    reserved credits to each affected user (idempotently — won't double-
    refund if a REFUND transaction already exists for the job), and pings
    each affected user so they know their stuck task was cancelled.
    """
    if message.from_user is None:
        return
    admin_ids = _get_admin_ids()
    if message.from_user.id not in admin_ids:
        return  # silent — non-admin

    db: Session = get_db_session()
    try:
        stuck = (
            db.query(GenerationJob)
            .filter(GenerationJob.status.in_([JobStatus.PENDING, JobStatus.PROCESSING]))
            .all()
        )
        total = len(stuck)
        if total == 0:
            await message.answer("✅ Очередь пуста — нечего обнулять.")
            return

        await message.answer(
            f"⏳ Обнуляю очередь: <b>{total}</b> задач...",
            parse_mode="HTML",
        )

        balance_service = BalanceService(db)
        refunded_users: dict[int, int] = {}  # telegram_user_id -> credits refunded
        refunded = 0
        skipped_refund = 0
        failed = 0

        for job in stuck:
            try:
                job.status = JobStatus.FAILED
                job.error_message = "Очередь сброшена администратором"

                # Refund — idempotent
                already_refunded = (
                    db.query(CreditTransaction)
                    .filter(
                        CreditTransaction.reference_type == "generation_job",
                        CreditTransaction.reference_id == str(job.id),
                        CreditTransaction.transaction_type == CreditTransactionType.REFUND,
                    )
                    .first()
                )
                if not already_refunded and (job.credits_reserved or 0) > 0:
                    balance_service.add_credits(
                        user_id=job.user_id,
                        amount=job.credits_reserved,
                        transaction_type=CreditTransactionType.REFUND,
                        reference_type="generation_job",
                        reference_id=str(job.id),
                        comment="Reset queue: admin refund",
                    )
                    refunded += 1
                    # Track per-user totals for the notification ping
                    user = db.query(User).filter(User.id == job.user_id).first()
                    if user:
                        refunded_users[user.telegram_user_id] = (
                            refunded_users.get(user.telegram_user_id, 0)
                            + job.credits_reserved
                        )
                else:
                    skipped_refund += 1
            except Exception as e:
                failed += 1
                logger.exception(f"[RESET_QUEUE] job {job.id} failed: {e}")

        db.commit()

        # Notify each affected user
        notified = 0
        for tg_id, credits in refunded_users.items():
            try:
                await bot.send_message(
                    chat_id=tg_id,
                    text=(
                        "⚠️ Ваша задача была отменена администратором "
                        "(очередь сброшена из-за сбоя).\n"
                        f"✅ Возвращено <b>{credits}</b> кр. на баланс."
                    ),
                    parse_mode="HTML",
                )
                notified += 1
            except TelegramForbiddenError:
                pass  # user blocked the bot
            except TelegramBadRequest:
                pass
            except Exception as e:
                logger.warning(f"[RESET_QUEUE] notify {tg_id} failed: {e}")

        await message.answer(
            "✅ <b>Очередь обнулена</b>\n\n"
            f"📋 Задач помечено FAILED: <b>{total}</b>\n"
            f"💰 Refund-транзакций создано: <b>{refunded}</b>\n"
            f"⏭ Уже было refund / 0 кр: <b>{skipped_refund}</b>\n"
            f"⚠️ Ошибок: <b>{failed}</b>\n"
            f"📨 Юзеров уведомлено: <b>{notified}</b>",
            parse_mode="HTML",
        )
    finally:
        db.close()
