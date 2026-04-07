"""
Google Sheets logging for all financial and credit events.

Sheet columns:
  Дата | Тип | ID | Пользователь | Username | Telegram ID | Описание | Сумма (сум) | Кредиты | API стоимость ($) | Статус | Комментарий
"""
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1bXXHSV6NOg8PfIFabML5_kc_oivQjq-JH9drsacOe6Q"
SHEET_NAME = "Sheet1"
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
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        info = json.loads(sa_json)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file(
            os.path.abspath(SERVICE_ACCOUNT_FILE), scopes=scopes
        )
    return gspread.authorize(creds)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")


def _fmt(n: int | float) -> str:
    return f"{int(n):,}".replace(",", " ")


HEADERS = [
    "Дата", "Тип", "ID", "Пользователь", "Username", "Telegram ID",
    "Описание", "Сумма (сум)", "Кредиты", "API стоимость", "Статус", "Комментарий"
]


def ensure_headers() -> None:
    """Write header row if row 1 is empty. Safe to call multiple times."""
    try:
        gc = _get_client()
        ws = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        first = ws.row_values(1)
        if not first or first[0] != "Дата":
            ws.insert_row(HEADERS, index=1)
            logger.info("[SHEETS] Headers written to Sheet1")
    except Exception as e:
        logger.error(f"[SHEETS] ensure_headers failed: {e}")


def _append(row: list) -> None:
    """Append one row to Sheet1. Never raises."""
    try:
        gc = _get_client()
        ws = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        ws.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        logger.error(f"[SHEETS] append failed: {e}")


# ─── Payment: credit package purchase ────────────────────────────────────────

def log_payment_confirmed(
    payment_id: int,
    user_full_name: str,
    username: str | None,
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


def log_payment_rejected(
    payment_id: int,
    user_full_name: str,
    username: str | None,
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


# ─── UZS balance top-up ───────────────────────────────────────────────────────

def log_uzs_topup_confirmed(
    user_full_name: str,
    username: str | None,
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


def log_uzs_topup_rejected(
    user_full_name: str,
    username: str | None,
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
    username: str | None,
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
    referrer_username: str | None,
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


# ─── Generation (credit usage) ────────────────────────────────────────────────

def log_generation(
    user_full_name: str,
    username: str | None,
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
        provider_label, "",  str(credits_used),
        f"≈${api_cost_usd} (≈{_fmt(api_cost_uzs)} сум)", "✅ Запущено", "",
    ])
    logger.info(f"[SHEETS] generation job#{job_id} for {telegram_id}: {credits_used}cr, ${api_cost_usd}")
