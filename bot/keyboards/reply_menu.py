from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types.web_app_info import WebAppInfo
from backend.core.config import settings

def main_reply_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎨 Yaratish"),
                 KeyboardButton(text="💎 Tariflar")],
                [KeyboardButton(text="❓ Yordam")],
                [KeyboardButton(
                    text="🌐 Shaxsiy kabinet",
                    web_app=WebAppInfo(url=settings.miniapp_url)
                )],
            ],
            resize_keyboard=True,
            persistent=True
        )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎨 Создать"),
             KeyboardButton(text="💎 Тарифы")],
            [KeyboardButton(text="❓ Помощь")],
            [KeyboardButton(
                text="🌐 Открыть кабинет",
                web_app=WebAppInfo(url=settings.miniapp_url)
            )],
        ],
        resize_keyboard=True,
        persistent=True
    )


REPLY_BUTTON_ACTIONS = {
    # RU
    "🎨 Создать":      "menu_create",
    # UZ
    "🎨 Yaratish":     "menu_create",
}
