"""
Multi-tab Google Sheets monitoring service.

Tabs:
  📊 Дашборд       — summary dashboard with auto-formulas
  👥 Пользователи  — new user registrations
  💳 Оплаты        — payment requests & confirmations
  🎨 Генерации     — generation jobs (start / complete / fail)
  ⚠️ Ошибки        — system errors
  📅 Дневник       — daily summary (written by Celery Beat at 23:59)

IMPORTANT: amount/numeric columns are stored as raw int/float
so Google Sheets can sum/average them with formulas.
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
TAB_DASHBOARD   = "📊 Дашборд"
TAB_USERS       = "👥 Пользователи"
TAB_PAYMENTS    = "💳 Оплаты"
TAB_GENERATIONS = "🎨 Генерации"
TAB_ERRORS      = "⚠️ Ошибки"
TAB_DIARY       = "📅 Дневник"

# ─── Column headers ──────────────────────────────────────────────────────────
# IMPORTANT: column order here defines column letters used in Dashboard formulas.
# Оплаты:     H=Сумма(сум)  I=Кредиты  J=Статус  C=Тип
# Генерации:  H=Кредиты  I=Статус  J=API($)  K=Время(сек)
# Пользователи: F=Источник  G=Реферер
# Дневник:    G=Выручка(сум)  I=API($)

HEADERS: dict[str, list[str]] = {
    TAB_DASHBOARD: ["Показатель", "Значение", "Единица / Примечание"],
    TAB_USERS: [
        "Дата", "Telegram ID", "Имя", "Username", "Язык",
        "Источник", "Реферер (tg_id)", "Стартовые кредиты",
    ],
    TAB_PAYMENTS: [
        "Дата", "ID", "Тип", "Telegram ID", "Имя", "Username",
        "Пакет / Описание", "Сумма (сум)", "Кредиты", "Статус", "Комментарий",
    ],
    TAB_GENERATIONS: [
        "Дата", "Job ID", "Telegram ID", "Имя", "Username",
        "Провайдер", "Промпт (100 симв)", "Кредиты", "Статус",
        "API стоимость ($)", "Время (сек)", "Комментарий",
    ],
    TAB_ERRORS: [
        "Дата", "Уровень", "Источник", "Telegram ID",
        "Job ID", "Сообщение", "Traceback",
    ],
    TAB_DIARY: [
        "Дата", "Новых польз.", "Генераций всего",
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


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _spreadsheet_id() -> str:
    from backend.core.config import settings
    sid = getattr(settings, "google_sheets_id", "") or ""
    return sid.strip() or _FALLBACK_SPREADSHEET_ID


def _get_client():
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
    """Return worksheet, creating it with headers if it doesn't exist."""
    gc = _get_client()
    sh = gc.open_by_key(_spreadsheet_id())
    try:
        ws = sh.worksheet(tab_name)
    except Exception:
        rows = 5000 if tab_name in (TAB_PAYMENTS, TAB_GENERATIONS) else 2000
        ws = sh.add_worksheet(title=tab_name, rows=rows, cols=20)
        ws.append_row(HEADERS.get(tab_name, []), value_input_option="USER_ENTERED")
        logger.info(f"[SHEETS] Created tab '{tab_name}'")
    return ws


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")


def _int(n: Union[int, float, None]) -> int:
    """Return raw int for numeric cells — so Sheets can SUM them."""
    if n is None:
        return 0
    return int(n)


def _float2(n: Union[int, float, None]) -> float:
    """Return rounded float for monetary/cost cells."""
    if n is None:
        return 0.0
    return round(float(n), 4)


def _append(tab: str, row: list) -> None:
    """Append one row to a tab."""
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
        _now(),
        telegram_id,          # raw int → Telegram ID
        full_name,
        uname,
        lang,
        source,
        ref,
        start_credits,        # raw int → Стартовые кредиты
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
        telegram_id, full_name, uname,
        plan_name,
        _int(amount_uzs),     # ← raw int: SUMIF works
        _int(credits),
        "⏳ Ожидание", "",
    ])


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
        telegram_id, full_name, uname,
        plan_name,
        _int(amount_uzs),     # ← raw int
        _int(credits),
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
        telegram_id, full_name, uname,
        plan_name,
        _int(amount_uzs),     # ← raw int
        0,
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
        referrer_telegram_id, referrer_name, uname,
        f"Комиссия за реферала ({referred_name})",
        _int(commission_uzs),  # ← raw int
        0,
        "✅ Начислено", "",
    ])
    logger.info(f"[SHEETS] referral commission {commission_uzs} UZS for {referrer_telegram_id}")


def log_balance_payment(
    telegram_id: int,
    full_name: str,
    username: Optional[str],
    plan_name: str,
    amount_uzs: int,
    credits: int = 0,
) -> None:
    """Payment from UZS balance."""
    log_payment_confirmed(
        payment_id=0,
        payment_type="💸 Оплата с баланса",
        telegram_id=telegram_id,
        full_name=full_name,
        username=username,
        plan_name=plan_name,
        amount_uzs=amount_uzs,
        credits=credits,
    )


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
    api_cost = _float2(API_COST_USD.get(provider, 0))
    _append(TAB_GENERATIONS, [
        _now(), job_id,
        telegram_id, full_name, uname,
        _provider_label(provider), (prompt or "")[:100],
        _int(credits), "🔄 Запущено",
        api_cost,        # ← raw float: SUM works
        0, "",
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
    api_cost = _float2(API_COST_USD.get(provider, 0))
    _append(TAB_GENERATIONS, [
        _now(), job_id,
        telegram_id, full_name, uname,
        _provider_label(provider), (prompt or "")[:100],
        _int(credits), "✅ Готово",
        api_cost,        # ← raw float
        _int(elapsed_seconds), "",
    ])
    logger.info(f"[SHEETS] generation complete job#{job_id} in {elapsed_seconds}s")


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
    api_cost = _float2(API_COST_USD.get(provider, 0))
    _append(TAB_GENERATIONS, [
        _now(), job_id,
        telegram_id, full_name, uname,
        _provider_label(provider), (prompt or "")[:100],
        _int(credits), "❌ Ошибка",
        api_cost,        # ← counted as cost even if failed
        0, (error or "")[:200],
    ])
    logger.info(f"[SHEETS] generation failed job#{job_id}: {error[:80]}")


def _provider_label(provider: str) -> str:
    return {
        "nano_banana": "🍌 Nano Banana",
        "kling":       "🎥 Kling",
        "veo":         "🎬 Veo 3",
    }.get(provider or "", provider or "—")


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
        (message or "")[:300], (tb or "")[:500],
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
        _int(new_users),
        _int(total_gens),
        _int(ok_gens),
        _int(fail_gens),
        _int(confirmed_payments),
        _int(revenue_uzs),      # ← raw int
        _int(credits_sold),
        _float2(api_cost_usd),  # ← raw float
        _int(errors),
    ])
    logger.info(f"[SHEETS] daily summary written for {row_date}")
