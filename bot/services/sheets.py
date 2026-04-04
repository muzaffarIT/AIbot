"""
Google Sheets logging for payments.
Appends a row to the configured spreadsheet when payment is confirmed or rejected.

Sheet columns (in order):
  Дата | № заявки | Пользователь | Username | Telegram ID | Пакет | Сумма (сум) | Статус | Комментарий
"""
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SPREADSHEET_ID = "1bXXHSV6NOg8PfIFabML5_kc_oivQjq-JH9drsacOe6Q"
SHEET_NAME = "Sheet1"
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "service_account.json")


def _get_client():
    import json
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # Prefer env var (for Railway) over local file
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        info = json.loads(sa_json)
        creds = Credentials.from_service_account_info(info, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file(
            os.path.abspath(SERVICE_ACCOUNT_FILE), scopes=scopes
        )
    return gspread.authorize(creds)


def log_payment_confirmed(
    payment_id: int,
    user_full_name: str,
    username: str | None,
    telegram_id: int,
    plan_name: str,
    amount_uzs: int,
) -> None:
    """Append a confirmed payment row to Google Sheets. Never raises — only logs errors."""
    try:
        gc = _get_client()
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet(SHEET_NAME)

        now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
        uname = f"@{username}" if username else "—"
        amount_fmt = f"{amount_uzs:,}".replace(",", " ")

        ws.append_row(
            [now, f"#{payment_id}", user_full_name, uname, str(telegram_id),
             plan_name, amount_fmt, "✅ Подтверждено", ""],
            value_input_option="USER_ENTERED",
        )
        logger.info(f"[SHEETS] Logged confirmed payment #{payment_id}")
    except Exception as e:
        logger.error(f"[SHEETS] Failed to log confirmed payment #{payment_id}: {e}")


def log_payment_rejected(
    payment_id: int,
    user_full_name: str,
    username: str | None,
    telegram_id: int,
    plan_name: str,
    amount_uzs: int,
    reason: str,
) -> None:
    """Append a rejected payment row to Google Sheets. Never raises — only logs errors."""
    try:
        gc = _get_client()
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet(SHEET_NAME)

        now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
        uname = f"@{username}" if username else "—"
        amount_fmt = f"{amount_uzs:,}".replace(",", " ")

        ws.append_row(
            [now, f"#{payment_id}", user_full_name, uname, str(telegram_id),
             plan_name, amount_fmt, "❌ Отклонено", reason],
            value_input_option="USER_ENTERED",
        )
        logger.info(f"[SHEETS] Logged rejected payment #{payment_id}")
    except Exception as e:
        logger.error(f"[SHEETS] Failed to log rejected payment #{payment_id}: {e}")
