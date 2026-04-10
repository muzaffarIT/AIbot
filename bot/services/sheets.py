"""
Google Sheets logging for all financial and credit events.

Sheet columns:
  Дата | Тип | ID | Пользователь | Username | Telegram ID | Описание | Сумма (сум) | Кредиты | API стоимость ($) | Статус | Комментарий
"""
from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime, timezone
from typing import Optional, Union

logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1bXXHSV6NOg8PfIFabML5_kc_oivQjq-JH9drsacOe6Q"
SHEET_NAME = "Лист1"   # actual tab name — use get_worksheet(0) as fallback
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "service_account.json")

# Approximate API costs per generation (USD) — for transparency reporting
API_COST_USD = {
    "nano_banana": 0.004,   # ~$0.004 per image
    "kling":       0.14,    # ~$0.14 per video
    "veo":         0.10,    # ~$0.10 per video (estimate)
}

# UZS per 1 USD (approximate, update as needed)
USD_TO_UZS = 12_700


def _get_client():
    import json
    import gspread

    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if sa_json:
        try:
            info = json.loads(sa_json)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON: {e}") from e
        # gspread 6.x API — service_account_from_dict handles auth internally
        return gspread.service_account_from_dict(info)

    # Fallback: read from file (local dev)
    sa_file = os.path.abspath(SERVICE_ACCOUNT_FILE)
    if not os.path.exists(sa_file):
        raise RuntimeError(
            f"GOOGLE_SERVICE_ACCOUNT_JSON env var not set and "
            f"service_account.json not found at {sa_file}"
        )
    return gspread.service_account(filename=sa_file)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")


def _fmt(n: Union[int, float]) -> str:
    return f"{int(n):,}".replace(",", " ")


HEADERS = [
    "Дата", "Тип", "ID", "Пользователь", "Username", "Telegram ID",
    "Описание", "Сумма (сум)", "Кредиты", "API стоимость", "Статус", "Комментарий"
]


def _get_worksheet():
    """Open the spreadsheet and return the first worksheet (robust to tab renames)."""
    gc = _get_client()
    sh = gc.open_by_key(SPREADSHEET_ID)
    # Try configured name first, fall back to first sheet if not found
    try:
        return sh.worksheet(SHEET_NAME)
    except Exception:
        return sh.get_worksheet(0)


def ensure_headers() -> None:
    """Write header row if row 1 is empty. Safe to call multiple times."""
    try:
        ws = _get_worksheet()
        first = ws.row_values(1)
        if not first or first[0] != "Дата":
            ws.insert_row(HEADERS, index=1)
            logger.info(f"[SHEETS] Headers written to '{ws.title}'")
        else:
            logger.info(f"[SHEETS] Headers OK on '{ws.title}'")
    except Exception as e:
        logger.error(f"[SHEETS] ensure_headers failed: {e}\n{traceback.format_exc()}")


def _append(row: list) -> None:
    """Append one row. Logs full traceback on failure."""
    try:
        ws = _get_worksheet()
        ws.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        logger.error(f"[SHEETS] append failed: {e}\n{traceback.format_exc()}")


def sheets_test() -> dict:
    """Connectivity test — call from /api/debug/sheets-test to verify setup."""
    try:
        ws = _get_worksheet()
        first = ws.row_values(1)
        return {"ok": True, "tab": ws.title, "headers": first}
    except Exception as e:
        return {"ok": False, "error": str(e), "traceback": traceback.format_exc()}


# ─── Payment: credit package purchase ────────────────────────────────────────

def log_payment_confirmed(
    payment_id: int,
    user_full_name: str,
    username: Optional[str],
    telegram_id: int,
    plan_name: str,
    amount_uzs: int,
    credits: int = 0,
) -> None:
    uname = f"@{username}" if username else "—"
    _append([
        _now(), "💳 Покупка пакета", f"#{payment_id}",
        user_full_name, uname, str(telegram_id),
        plan_name, _fmt(amount_uzs), str(credits),
        "", "✅ Подтверждено", "",
    ])
    logger.info(f"[SHEETS] payment confirmed #{payment_id}")
    # Also log to multi-tab service
    try:
        from backend.services.sheets_service import log_payment_confirmed as _lpc
        _lpc(
            payment_id=payment_id, payment_type="💳 Покупка пакета",
            telegram_id=telegram_id, full_name=user_full_name, username=username,
            plan_name=plan_name, amount_uzs=amount_uzs, credits=credits,
        )
    except Exception as _e:
        logger.error(f"[SHEETS_MT] log_payment_confirmed failed: {_e}")


def log_payment_rejected(
    payment_id: int,
    user_full_name: str,
    username: Optional[str],
    telegram_id: int,
    plan_name: str,
    amount_uzs: int,
    reason: str,
) -> None:
    uname = f"@{username}" if username else "—"
    _append([
        _now(), "❌ Отклонено (пакет)", f"#{payment_id}",
        user_full_name, uname, str(telegram_id),
        plan_name, _fmt(amount_uzs), "",
        "", "❌ Отклонено", reason,
    ])
    logger.info(f"[SHEETS] payment rejected #{payment_id}")
    try:
        from backend.services.sheets_service import log_payment_rejected as _lpr
        _lpr(
            payment_id=payment_id, payment_type="💳 Покупка пакета",
            telegram_id=telegram_id, full_name=user_full_name, username=username,
            plan_name=plan_name, amount_uzs=amount_uzs, reason=reason,
        )
    except Exception as _e:
        logger.error(f"[SHEETS_MT] log_payment_rejected failed: {_e}")


# ─── UZS balance top-up ───────────────────────────────────────────────────────

def log_uzs_topup_confirmed(
    user_full_name: str,
    username: Optional[str],
    telegram_id: int,
    amount_uzs: int,
) -> None:
    uname = f"@{username}" if username else "—"
    _append([
        _now(), "💵 Пополнение баланса", "—",
        user_full_name, uname, str(telegram_id),
        "Пополнение денежного баланса", _fmt(amount_uzs), "",
        "", "✅ Подтверждено", "",
    ])
    logger.info(f"[SHEETS] UZS topup confirmed for {telegram_id}: {amount_uzs}")
    try:
        from backend.services.sheets_service import log_uzs_topup_confirmed as _lutc
        _lutc(
            telegram_id=telegram_id, full_name=user_full_name,
            username=username, amount_uzs=amount_uzs,
        )
    except Exception as _e:
        logger.error(f"[SHEETS_MT] log_uzs_topup_confirmed failed: {_e}")


def log_uzs_topup_rejected(
    user_full_name: str,
    username: Optional[str],
    telegram_id: int,
    amount_uzs: int,
) -> None:
    uname = f"@{username}" if username else "—"
    _append([
        _now(), "❌ Отклонено (пополнение)", "—",
        user_full_name, uname, str(telegram_id),
        "Пополнение денежного баланса", _fmt(amount_uzs), "",
        "", "❌ Отклонено", "",
    ])
    logger.info(f"[SHEETS] UZS topup rejected for {telegram_id}")


# ─── Pay for plan from UZS balance ───────────────────────────────────────────

def log_balance_payment(
    user_full_name: str,
    username: Optional[str],
    telegram_id: int,
    plan_name: str,
    amount_uzs: int,
    credits: int,
) -> None:
    uname = f"@{username}" if username else "—"
    _append([
        _now(), "🔄 Оплата с баланса", "—",
        user_full_name, uname, str(telegram_id),
        plan_name, _fmt(amount_uzs), str(credits),
        "", "✅ Выполнено", "",
    ])
    logger.info(f"[SHEETS] balance payment for {telegram_id}: {plan_name}")


# ─── Referral commission ──────────────────────────────────────────────────────

def log_referral_commission(
    referrer_full_name: str,
    referrer_username: Optional[str],
    referrer_telegram_id: int,
    referred_full_name: str,
    commission_uzs: int,
) -> None:
    uname = f"@{referrer_username}" if referrer_username else "—"
    _append([
        _now(), "👥 Реферальная комиссия", "—",
        referrer_full_name, uname, str(referrer_telegram_id),
        f"Комиссия за пополнение реферала ({referred_full_name})", _fmt(commission_uzs), "",
        "", "✅ Начислено", "",
    ])
    logger.info(f"[SHEETS] referral commission {commission_uzs} for {referrer_telegram_id}")
    try:
        from backend.services.sheets_service import log_referral_commission as _lrc
        _lrc(
            referrer_telegram_id=referrer_telegram_id,
            referrer_name=referrer_full_name,
            referrer_username=referrer_username,
            referred_name=referred_full_name,
            commission_uzs=commission_uzs,
        )
    except Exception as _e:
        logger.error(f"[SHEETS_MT] log_referral_commission failed: {_e}")


# ─── Generation (credit usage) ────────────────────────────────────────────────

def log_generation(
    user_full_name: str,
    username: Optional[str],
    telegram_id: int,
    provider: str,
    credits_used: int,
    job_id: int,
) -> None:
    uname = f"@{username}" if username else "—"
    api_cost_usd = API_COST_USD.get(provider, 0)
    api_cost_uzs = int(api_cost_usd * USD_TO_UZS)
    provider_label = {
        "nano_banana": "🍌 Nano Banana",
        "kling": "🎥 Kling",
        "veo": "🎬 Veo 3",
    }.get(provider, provider)
    _append([
        _now(), "🎨 Генерация", f"job#{job_id}",
        user_full_name, uname, str(telegram_id),
        provider_label, "", str(credits_used),
        f"≈${api_cost_usd} (≈{_fmt(api_cost_uzs)} сум)", "✅ Запущено", "",
    ])
    logger.info(f"[SHEETS] generation job#{job_id} for {telegram_id}: {credits_used}cr, ${api_cost_usd}")
    # Multi-tab: log to 🎨 Генерации tab as well
    try:
        from backend.services.sheets_service import log_generation_started
        log_generation_started(
            job_id=job_id, telegram_id=telegram_id,
            full_name=user_full_name, username=username,
            provider=provider, prompt="", credits=credits_used,
        )
    except Exception as _e:
        logger.error(f"[SHEETS_MT] log_generation (started) failed: {_e}")
