from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types.web_app_info import WebAppInfo
from backend.core.config import settings

def main_reply_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Persistent reply keyboard.
    Layout:
      [🎨 Создать]
      [🌐 Открыть кабинет] (WebApp)
    """
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎨 Yaratish")],
                [KeyboardButton(
                    text="🌐 Kabinetni ochish",
                    web_app=WebAppInfo(url=settings.miniapp_url or "")
                )],
            ],
            resize_keyboard=True,
            persistent=True,
            is_persistent=True,
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🎨 Создать")],
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
    "🎨 Создать":      "menu_create",
    # UZ
    "🎨 Yaratish":     "menu_create",
}
