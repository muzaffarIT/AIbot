from aiogram.types import (ReplyKeyboardMarkup,
                            KeyboardButton, WebAppInfo)
from backend.core.config import settings

def main_reply_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎨 Yaratish"),
                 KeyboardButton(text="💎 Tariflar")],
                [KeyboardButton(text="📊 Ishlarim"),
                 KeyboardButton(text="💰 Balans")],
                [KeyboardButton(text="👥 Hamkorlik"),
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
             KeyboardButton(text="💎 Тарифы")],
            [KeyboardButton(text="📊 История"),
             KeyboardButton(text="💰 Баланс")],
            [KeyboardButton(text="👥 Партнёрам"),
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
    "🎨 Создать":      "menu_create",
    "💎 Тарифы":       "menu_plans",
    "📊 История":      "history_cmd",
    "💰 Баланс":       "menu_balance",
    "👥 Партнёрам":    "menu_referral",
    "❓ Помощь":       "menu_help",
    "🌍 Язык":         "menu_language",
    # UZ
    "🎨 Yaratish":     "menu_create",
    "💎 Tariflar":     "menu_plans",
    "📊 Ishlarim":     "history_cmd",
    "💰 Balans":       "menu_balance",
    "👥 Hamkorlik":    "menu_referral",
    "❓ Yordam":       "menu_help",
    "🌍 Til":          "menu_language",
}
