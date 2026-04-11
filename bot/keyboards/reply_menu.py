from aiogram.types import (ReplyKeyboardMarkup,
                            KeyboardButton, WebAppInfo)
from backend.core.config import settings

def main_reply_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎨 Yaratish"),
                 KeyboardButton(text="❓ Yordam")],
                [KeyboardButton(text="🌍 Til")],
                [KeyboardButton(
                    text="🌐 Kabinetni ochish",
                    web_app=WebAppInfo(url=(settings.miniapp_url or "").rstrip("/"))
                )],
            ],
            resize_keyboard=True,
            persistent=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎨 Создать"),
             KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(text="🌍 Язык")],
            [KeyboardButton(
                text="🌐 Открыть кабинет",
                web_app=WebAppInfo(url=(settings.miniapp_url or "").rstrip("/"))
            )],
        ],
        resize_keyboard=True,
        persistent=True
    )


REPLY_BUTTON_ACTIONS = {
    # RU
    "🎨 Создать":   "menu_create",
    "❓ Помощь":    "menu_help",
    "🌍 Язык":      "menu_language",
    # UZ
    "🎨 Yaratish":  "menu_create",
    "❓ Yordam":    "menu_help",
    "🌍 Til":       "menu_language",
}
