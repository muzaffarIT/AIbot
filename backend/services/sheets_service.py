"""
Multi-tab Google Sheets monitoring service.

Tabs:
  👥 Пользователи  — new user registrations
  💳 Оплаты        — payment requests & confirmations
  🎨 Генерации     — generation jobs (start / complete / fail)
  ⚠️ Ошибки        — system errors
  📅 Дневник       — daily summary (written by Celery Beat at 23:59)
"""
from __future__ import annotations

import logging
import os
import traceback
import threading
from datetime import datetime, timezone
from typing import Optional, Union

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

_FALLBACK_SPREADSHEET_ID = "1bXXHSV6NOg8PfIFabML5_kc_oivQjq-JH9drsacOe6Q"
_SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "service_account.json"
)

# Tab names
TAB_USERS       = "👥 Пользователи"
TAB_PAYMENTS    = "💳 Оплаты"
TAB_GENERATIONS = "🎨 Генерации"
TAB_ERRORS      = "⚠️ Ошибки"
TAB_DIARY       = "📅 Дневник"

# Headers per tab
HEADERS: dict[str, list[str]] = {
    TAB_USERS: [
        "Дата", "Telegram ID", "Имя", "Username", "Язык",
        "Источник", "Реферер", "Стартовые кредиты",
    ],
    TAB_PAYMENTS: [
        "Дата", "ID", "Тип", "Telegram ID", "Имя", "Username",
        "Пакет / Сумма", "Сумма (сум)", "Кредиты", "Статус", "Комментарий",
    ],
    TAB_GENERATIONS: [
        "Дата", "Job ID", "Telegram ID", "Имя", "Username",
        "Провайдер", "Промпт (100)", "Кредиты", "Статус",
        "API стоимость ($)", "Время (сек)", "Комментарий",
    ],
    TAB_ERRORS: [
        "Дата", "Уровень", "Источник", "Telegram ID",
        "Job ID", "Сообщение", "Traceback",
    ],
    TAB_DIARY: [
        "Дата", "Новых пользователей", "Генераций (всего)",
        "Генераций OK", "Генераций FAIL",
        "Оплат подтверждено", "Выручка (сум)", "Кредитов продано",
        "API расход ($)", "Ошибок",
    ],
}

# Approximate API costs per generation (USD)
API_COST_USD: dict[str, float] = {
    "nano_banana": 0.004,
    "kling":       0.14,
    "veo":         0.10,
}

_lock = threading.Lock()
_gc_cache: object = None  # cached gspread client


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _spreadsheet_id() -> str:
    from backend.core.config import settings
    sid = getattr(settings, "google_sheets_id", "") or ""
    return sid.strip() or _FALLBACK_SPREADSHEET_ID


def _get_client():
    """Return a gspread client, reusing the cached one when possible."""
    global _gc_cache
    import json
    import gspread

    sa_json = (
        os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        or _try_setting("google_credentials_json")
    )
    if sa_json:
        try:
            info = json.loads(sa_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Invalid service account JSON: {exc}") from exc
        return gspread.service_account_from_dict(info)

    sa_file = os.path.abspath(_SERVICE_ACCOUNT_FILE)
    if os.path.exists(sa_file):
        return gspread.service_account(filename=sa_file)

    raise RuntimeError(
        "Neither GOOGLE_SERVICE_ACCOUNT_JSON env var nor service_account.json found"
    )


def _try_setting(attr: str) -> str:
    try:
        from backend.core.config import settings
        return getattr(settings, attr, "") or ""
    except Exception:
        return ""


def _get_worksheet(tab_name: str):
    """Return worksheet by name, creating it (with headers) if it doesn't exist."""
    gc = _get_client()
    sh = gc.open_by_key(_spreadsheet_id())

    try:
        ws = sh.worksheet(tab_name)
    except Exception:
        ws = sh.add_worksheet(title=tab_name, rows=1000, cols=20)
        ws.append_row(HEADERS.get(tab_name, []), value_input_option="USER_ENTERED")
        logger.info(f"[SHEETS] Created tab '{tab_name}'")
    return ws


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")


def _fmt(n: Union[int, float, None]) -> str:
    if n is None:
        return "0"
    return f"{int(n):,}".replace(",", " ")


def _append(tab: str, row: list) -> None:
    """Append one row to the given tab, with full error logging."""
    try:
        with _lock:
            ws = _get_worksheet(tab)
            ws.append_row(row, value_input_option="USER_ENTERED")
    except Exception as exc:
        logger.error(
            f"[SHEETS] append to '{tab}' failed: {exc}\n{traceback.format_exc()}"
        )


# ─── 👥 Пользователи ─────────────────────────────────────────────────────────

def log_new_user(
    telegram_id: int,
    full_name: str,
    username: Optional[str],
    lang: str,
    source: str = "organic",
    referrer_telegram_id: Optional[int] = None,
    start_credits: int = 0,
) -> None:
    uname = f"@{username}" if username else "—"
    ref = str(referrer_telegram_id) if referrer_telegram_id else "—"
    _append(TAB_USERS, [
        _now(), str(telegram_id), full_name, uname,
        lang, source, ref, str(start_credits),
    ])
    logger.info(f"[SHEETS] new user {telegram_id}")


# ─── 💳 Оплаты ───────────────────────────────────────────────────────────────

def log_payment_request(
    payment_id: int,
    payment_type: str,
    telegram_id: int,
    full_name: str,
    username: Optional[str],
    plan_name: str,
    amount_uzs: int,
    credits: int = 0,
) -> None:
    uname = f"@{username}" if username else "—"
    _append(TAB_PAYMENTS, [
        _now(), f"#{payment_id}", payment_type,
        str(telegram_id), full_name, uname,
        plan_name, _fmt(amount_uzs), str(credits) if credits else "",
        "⏳ Ожидание", "",
    ])
    logger.info(f"[SHEETS] payment request #{payment_id}")


def log_payment_confirmed(
    payment_id: int,
    payment_type: str,
    telegram_id: int,
    full_name: str,
    username: Optional[str],
    plan_name: str,
    amount_uzs: int,
    credits: int = 0,
    comment: str = "",
) -> None:
    uname = f"@{username}" if username else "—"
    _append(TAB_PAYMENTS, [
        _now(), f"#{payment_id}", payment_type,
        str(telegram_id), full_name, uname,
        plan_name, _fmt(amount_uzs), str(credits) if credits else "",
        "✅ Подтверждено", comment,
    ])
    logger.info(f"[SHEETS] payment confirmed #{payment_id}")


def log_payment_rejected(
    payment_id: int,
    payment_type: str,
    telegram_id: int,
    full_name: str,
    username: Optional[str],
    plan_name: str,
    amount_uzs: int,
    reason: str = "",
) -> None:
    uname = f"@{username}" if username else "—"
    _append(TAB_PAYMENTS, [
        _now(), f"#{payment_id}", payment_type,
        str(telegram_id), full_name, uname,
        plan_name, _fmt(amount_uzs), "",
        "❌ Отклонено", reason,
    ])
    logger.info(f"[SHEETS] payment rejected #{payment_id}")


def log_uzs_topup_confirmed(
    telegram_id: int,
    full_name: str,
    username: Optional[str],
    amount_uzs: int,
    comment: str = "",
) -> None:
    log_payment_confirmed(
        payment_id=0,
        payment_type="💵 Пополнение баланса",
        telegram_id=telegram_id,
        full_name=full_name,
        username=username,
        plan_name="Пополнение денежного баланса",
        amount_uzs=amount_uzs,
        comment=comment,
    )


def log_referral_commission(
    referrer_telegram_id: int,
    referrer_name: str,
    referrer_username: Optional[str],
    referred_name: str,
    commission_uzs: int,
) -> None:
    uname = f"@{referrer_username}" if referrer_username else "—"
    _append(TAB_PAYMENTS, [
        _now(), "—", "👥 Реферальная комиссия",
        str(referrer_telegram_id), referrer_name, uname,
        f"Комиссия за реферала ({referred_name})", _fmt(commission_uzs), "",
        "✅ Начислено", "",
    ])
    logger.info(f"[SHEETS] referral commission {commission_uzs} for {referrer_telegram_id}")


# ─── 🎨 Генерации ─────────────────────────────────────────────────────────────

def log_generation_started(
    job_id: int,
    telegram_id: int,
    full_name: str,
    username: Optional[str],
    provider: str,
    prompt: str,
    credits: int,
) -> None:
    uname = f"@{username}" if username else "—"
    api_cost = API_COST_USD.get(provider, 0)
    _append(TAB_GENERATIONS, [
        _now(), str(job_id),
        str(telegram_id), full_name, uname,
        _provider_label(provider), prompt[:100],
        str(credits), "🔄 Запущено",
        f"≈${api_cost}", "", "",
    ])
    logger.info(f"[SHEETS] generation started job#{job_id}")


def log_generation_complete(
    job_id: int,
    telegram_id: int,
    full_name: str,
    username: Optional[str],
    provider: str,
    prompt: str,
    credits: int,
    elapsed_seconds: int = 0,
) -> None:
    uname = f"@{username}" if username else "—"
    api_cost = API_COST_USD.get(provider, 0)
    _append(TAB_GENERATIONS, [
        _now(), str(job_id),
        str(telegram_id), full_name, uname,
        _provider_label(provider), prompt[:100],
        str(credits), "✅ Готово",
        f"≈${api_cost}", str(elapsed_seconds), "",
    ])
    logger.info(f"[SHEETS] generation complete job#{job_id}")


def log_generation_failed(
    job_id: int,
    telegram_id: int,
    full_name: str,
    username: Optional[str],
    provider: str,
    prompt: str,
    credits: int,
    error: str = "",
) -> None:
    uname = f"@{username}" if username else "—"
    _append(TAB_GENERATIONS, [
        _now(), str(job_id),
        str(telegram_id), full_name, uname,
        _provider_label(provider), prompt[:100],
        str(credits), "❌ Ошибка",
        "", "", error[:200],
    ])
    logger.info(f"[SHEETS] generation failed job#{job_id}")


def _provider_label(provider: str) -> str:
    return {
        "nano_banana": "🍌 Nano Banana",
        "kling":       "🎥 Kling",
        "veo":         "🎬 Veo 3",
    }.get(provider, provider)


# ─── ⚠️ Ошибки ────────────────────────────────────────────────────────────────

def log_error(
    source: str,
    message: str,
    level: str = "ERROR",
    telegram_id: Optional[int] = None,
    job_id: Optional[int] = None,
    tb: str = "",
) -> None:
    _append(TAB_ERRORS, [
        _now(), level, source,
        str(telegram_id) if telegram_id else "—",
        str(job_id) if job_id else "—",
        message[:300], tb[:500],
    ])


# ─── 📅 Дневник (daily summary) ───────────────────────────────────────────────

def log_daily_summary(
    new_users: int,
    total_gens: int,
    ok_gens: int,
    fail_gens: int,
    confirmed_payments: int,
    revenue_uzs: int,
    credits_sold: int,
    api_cost_usd: float,
    errors: int,
    date: Optional[str] = None,
) -> None:
    row_date = date or datetime.now(timezone.utc).strftime("%d.%m.%Y")
    _append(TAB_DIARY, [
        row_date,
        str(new_users),
        str(total_gens),
        str(ok_gens),
        str(fail_gens),
        str(confirmed_payments),
        _fmt(revenue_uzs),
        str(credits_sold),
        f"${api_cost_usd:.3f}",
        str(errors),
    ])
    logger.info(f"[SHEETS] daily summary written for {row_date}")
