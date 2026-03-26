from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types.web_app_info import WebAppInfo
from backend.core.config import settings


def main_reply_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Persistent reply keyboard.
    Layout:
      [🎨 Создать] [💎 Тарифы]
      [❓ Помощь]
      [🌐 Открыть кабинет]  ← full width, WebApp
    """
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎨 Yaratish"),
                 KeyboardButton(text="💎 Tariflar")],
                [KeyboardButton(text="❓ Yordam")],
                [KeyboardButton(
                    text="🌐 Shaxsiy kabinet",
                    web_app=WebAppInfo(url=settings.miniapp_url or "")
                )],
            ],
            resize_keyboard=True,
            persistent=True,
            is_persistent=True,
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎨 Создать"),
             KeyboardButton(text="💎 Тарифы")],
            [KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(
                text="🌐 Открыть кабинет",
                web_app=WebAppInfo(url=settings.miniapp_url or "")
            )],
        ],
        resize_keyboard=True,
        persistent=True,
        is_persistent=True,
    )


REPLY_BUTTON_ACTIONS = {
    # RU
    "🎨 Создать":       "menu_create",
    "💎 Тарифы":        "menu_plans",
    "❓ Помощь":         "menu_help",
    # UZ
    "🎨 Yaratish":      "menu_create",
    "💎 Tariflar":      "menu_plans",
    "❓ Yordam":         "menu_help",
}
