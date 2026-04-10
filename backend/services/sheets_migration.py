"""
One-time historical data migration: DB → Google Sheets.

Migrates:
  👥 Пользователи  — all registered users
  💳 Оплаты        — all orders + credit transactions (referral, bonuses, refunds)
  🎨 Генерации     — all generation jobs
"""
from __future__ import annotations

import logging
import time
import traceback
from datetime import timezone
from typing import Optional

logger = logging.getLogger(__name__)

_BATCH = 400  # rows per gspread append_rows call (safe limit)


# ─── helpers ─────────────────────────────────────────────────────────────────

def _fmt_dt(dt) -> str:
    if dt is None:
        return "—"
    try:
        if dt.tzinfo is None:
            from datetime import timezone as tz
            dt = dt.replace(tzinfo=tz.utc)
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return str(dt)


def _fmt_num(n) -> str:
    if n is None:
        return "0"
    try:
        return f"{int(n):,}".replace(",", " ")
    except Exception:
        return str(n)


def _provider_label(provider: str) -> str:
    return {
        "nano_banana": "🍌 Nano Banana",
        "kling":       "🎥 Kling",
        "veo":         "🎬 Veo 3",
    }.get(provider, provider or "—")


def _batch_append(ws, rows: list) -> None:
    """Write rows to worksheet in batches, respecting rate limits."""
    for i in range(0, len(rows), _BATCH):
        chunk = rows[i:i + _BATCH]
        ws.append_rows(chunk, value_input_option="USER_ENTERED")
        if i + _BATCH < len(rows):
            time.sleep(1.5)  # small pause to avoid quota exhaustion


# ─── main migration ───────────────────────────────────────────────────────────

def migrate_all_to_sheets(clear_first: bool = True) -> dict:
    """
    Export all DB data to Google Sheets tabs.
    If clear_first=True — clears tabs (except row 1 header) before writing.
    Returns summary dict with row counts.
    """
    from backend.db.session import SessionLocal
    from backend.models.user import User
    from backend.models.generation_job import GenerationJob
    from backend.models.order import Order
    from backend.models.plan import Plan
    from backend.models.credit_transaction import CreditTransaction
    from backend.models.balance import Balance
    from backend.services.sheets_service import (
        _get_worksheet,
        TAB_USERS, TAB_PAYMENTS, TAB_GENERATIONS,
        HEADERS,
    )

    db = SessionLocal()
    summary: dict = {}
    errors: list = []

    try:
        # ── pre-load lookup maps ──────────────────────────────────────────────
        users = db.query(User).order_by(User.created_at).all()
        user_map: dict[int, User] = {u.id: u for u in users}
        tg_map: dict[int, User] = {u.telegram_user_id: u for u in users}

        plans = db.query(Plan).all()
        plan_map: dict[int, Plan] = {p.id: p for p in plans}

        balances = db.query(Balance).all()
        balance_map: dict[int, int] = {b.user_id: b.credits_balance for b in balances}

        logger.info(f"[MIGRATE] Loaded {len(users)} users, {len(plans)} plans")

        # ── 1. 👥 Пользователи ───────────────────────────────────────────────
        try:
            ws_users = _get_worksheet(TAB_USERS)
            if clear_first:
                ws_users.clear()
                ws_users.append_row(HEADERS[TAB_USERS], value_input_option="USER_ENTERED")
                time.sleep(0.5)

            rows_users = []
            for u in users:
                uname = f"@{u.username}" if u.username else "—"
                ref = str(u.referred_by_telegram_id) if u.referred_by_telegram_id else "—"
                source = f"ref_{u.referred_by_telegram_id}" if u.referred_by_telegram_id else "organic"
                credits_now = balance_map.get(u.id, 0)
                rows_users.append([
                    _fmt_dt(u.created_at),
                    str(u.telegram_user_id),
                    u.first_name or "—",
                    uname,
                    u.language_code or "ru",
                    source,
                    ref,
                    str(credits_now),   # current credit balance (historical not stored)
                ])

            if rows_users:
                _batch_append(ws_users, rows_users)
            summary[TAB_USERS] = len(rows_users)
            logger.info(f"[MIGRATE] Users: {len(rows_users)} rows written")

        except Exception as e:
            errors.append(f"Users: {e}")
            logger.error(f"[MIGRATE] Users failed: {e}\n{traceback.format_exc()}")

        # ── 2. 💳 Оплаты — orders ────────────────────────────────────────────
        try:
            ws_pay = _get_worksheet(TAB_PAYMENTS)
            if clear_first:
                ws_pay.clear()
                ws_pay.append_row(HEADERS[TAB_PAYMENTS], value_input_option="USER_ENTERED")
                time.sleep(0.5)

            orders = db.query(Order).order_by(Order.created_at).all()
            rows_orders = []
            for o in orders:
                u = user_map.get(o.user_id)
                p = plan_map.get(o.plan_id)
                full_name = (u.first_name or "—") if u else "—"
                uname = (f"@{u.username}" if u.username else "—") if u else "—"
                tg_id = str(u.telegram_user_id) if u else "—"
                plan_name = p.name if p else f"plan#{o.plan_id}"
                credits = p.credits_amount if p else 0

                status_emoji = {
                    "completed": "✅ Оплачено",
                    "pending": "⏳ Ожидание",
                    "failed": "❌ Ошибка",
                    "cancelled": "🚫 Отменено",
                }.get(o.status, o.status)

                rows_orders.append([
                    _fmt_dt(o.created_at),
                    f"#{o.id}",
                    "💳 Покупка пакета",
                    tg_id, full_name, uname,
                    plan_name,
                    int(o.amount),    # ← raw int: SUM works
                    credits if credits else 0,
                    status_emoji,
                    o.payment_method or "",
                ])

            if rows_orders:
                _batch_append(ws_pay, rows_orders)
            summary[TAB_PAYMENTS] = len(rows_orders)
            logger.info(f"[MIGRATE] Orders: {len(rows_orders)} rows written")

        except Exception as e:
            errors.append(f"Payments: {e}")
            logger.error(f"[MIGRATE] Payments failed: {e}\n{traceback.format_exc()}")

        # ── 2b. 💳 Оплаты — credit_transactions (referral/bonuses/refunds) ───
        try:
            ws_pay = _get_worksheet(TAB_PAYMENTS)
            INTERESTING = {
                "referral_commission", "referral_welcome", "referral_registration_bonus",
                "welcome_bonus", "daily_bonus", "refund",
                "referral", "manual_add", "admin_add",
            }
            txns = (
                db.query(CreditTransaction)
                .filter(CreditTransaction.transaction_type.in_(INTERESTING))
                .order_by(CreditTransaction.created_at)
                .all()
            )
            rows_txn = []
            for t in txns:
                u = user_map.get(t.user_id)
                full_name = (u.first_name or "—") if u else "—"
                uname = (f"@{u.username}" if u.username else "—") if u else "—"
                tg_id = str(u.telegram_user_id) if u else "—"

                type_labels = {
                    "referral_commission":        "👥 Реферальная комиссия",
                    "referral_welcome":           "🎁 Бонус рефералу",
                    "referral_registration_bonus": "🎁 Бонус за регистрацию реферала",
                    "welcome_bonus":              "🎁 Приветственный бонус",
                    "daily_bonus":                "📅 Ежедневный бонус",
                    "refund":                     "↩️ Возврат кредитов",
                    "referral":                   "👥 Реферал",
                    "manual_add":                 "🔧 Ручное начисление",
                    "admin_add":                  "🔧 Начисление администратором",
                }.get(t.transaction_type, t.transaction_type)

                rows_txn.append([
                    _fmt_dt(t.created_at),
                    f"tx#{t.id}",
                    type_labels,
                    tg_id, full_name, uname,
                    t.comment or "—",
                    0,              # no UZS amount for credit txns
                    int(t.amount),  # ← raw int: credits amount
                    "✅ Выполнено",
                    "",
                ])

            if rows_txn:
                _batch_append(ws_pay, rows_txn)
            summary[TAB_PAYMENTS] = summary.get(TAB_PAYMENTS, 0) + len(rows_txn)
            logger.info(f"[MIGRATE] Credit txns: {len(rows_txn)} rows written")

        except Exception as e:
            errors.append(f"Credit txns: {e}")
            logger.error(f"[MIGRATE] Credit txns failed: {e}\n{traceback.format_exc()}")

        # ── 3. 🎨 Генерации ──────────────────────────────────────────────────
        try:
            ws_gen = _get_worksheet(TAB_GENERATIONS)
            if clear_first:
                ws_gen.clear()
                ws_gen.append_row(HEADERS[TAB_GENERATIONS], value_input_option="USER_ENTERED")
                time.sleep(0.5)

            API_COST = {"nano_banana": 0.004, "kling": 0.14, "veo": 0.10}
            jobs = db.query(GenerationJob).order_by(GenerationJob.created_at).all()
            rows_gen = []
            for j in jobs:
                u = user_map.get(j.user_id)
                full_name = (u.first_name or "—") if u else "—"
                uname = (f"@{u.username}" if u.username else "—") if u else "—"
                tg_id = str(u.telegram_user_id) if u else "—"

                elapsed = ""
                if j.completed_at and j.created_at:
                    try:
                        ca = j.created_at
                        co = j.completed_at
                        if ca.tzinfo is None:
                            from datetime import timezone as tz
                            ca = ca.replace(tzinfo=tz.utc)
                        if co.tzinfo is None:
                            from datetime import timezone as tz
                            co = co.replace(tzinfo=tz.utc)
                        elapsed = str(int((co - ca).total_seconds()))
                    except Exception:
                        pass

                status_map = {
                    "completed": "✅ Готово",
                    "failed":    "❌ Ошибка",
                    "pending":   "⏳ Ожидание",
                    "processing": "🔄 В процессе",
                    "cancelled": "🚫 Отменено",
                }
                status = status_map.get(j.status, j.status)
                api_cost = API_COST.get(j.provider, 0.01)
                comment = j.error_message[:200] if j.error_message else ""

                rows_gen.append([
                    _fmt_dt(j.created_at),
                    j.id,               # raw int
                    tg_id, full_name, uname,
                    _provider_label(j.provider),
                    (j.prompt or "")[:100],
                    j.credits_reserved, # raw int
                    status,
                    round(api_cost, 4), # raw float: SUM works
                    int(elapsed) if elapsed else 0,
                    comment,
                ])

            if rows_gen:
                _batch_append(ws_gen, rows_gen)
            summary[TAB_GENERATIONS] = len(rows_gen)
            logger.info(f"[MIGRATE] Generation jobs: {len(rows_gen)} rows written")

        except Exception as e:
            errors.append(f"Generations: {e}")
            logger.error(f"[MIGRATE] Generations failed: {e}\n{traceback.format_exc()}")

    finally:
        db.close()

    result = {
        "status": "ok" if not errors else "partial",
        "rows_written": summary,
        "total": sum(summary.values()),
    }
    if errors:
        result["errors"] = errors
    return result
