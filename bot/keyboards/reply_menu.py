from aiogram.types import (ReplyKeyboardMarkup,
                            KeyboardButton, WebAppInfo)
from backend.core.config import settings

def main_reply_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """Persistent keyboard — the mini app takes the top, full-width row."""
    miniapp_url = (settings.miniapp_url or "").rstrip("/")
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(
                    text="✨ HARF AI'ni ochish",
                    web_app=WebAppInfo(url=miniapp_url),
                )],
                [KeyboardButton(text="🎨 Botda yaratish"),
                 KeyboardButton(text="❓ Yordam")],
                [KeyboardButton(text="☀️ Bonus"),
                 KeyboardButton(text="🌍 Til")],
            ],
            resize_keyboard=True,
            persistent=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="✨ Открыть HARF AI",
                web_app=WebAppInfo(url=miniapp_url),
            )],
            [KeyboardButton(text="🎨 Создать в боте"),
             KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="☀️ Бонус"),
             KeyboardButton(text="🌍 Язык")],
        ],
        resize_keyboard=True,
        persistent=True
    )


REPLY_BUTTON_ACTIONS = {
    # RU
    "🎨 Создать в боте": "menu_create",
    "❓ Помощь":         "menu_help",
    "🌍 Язык":           "menu_language",
    "☀️ Бонус":          "daily_bonus",
    # UZ
    "🎨 Botda yaratish": "menu_create",
    "❓ Yordam":         "menu_help",
    "🌍 Til":            "menu_language",
    "☀️ Bonus":          "daily_bonus",
    # Legacy labels — existing users keep a cached keyboard until they press
    # something that re-sends it, so the old texts must still resolve.
    "🎨 Создать":   "menu_create",
    "🎨 Yaratish":  "menu_create",
}
