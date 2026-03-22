"""
Handler for the 🌐 Кабинет / 🌐 Kabinet reply keyboard button.
Opens the Mini App via inline WebApp button.
"""
from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.core.config import settings
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()


@router.message(F.text.in_(["🌐 Кабинет", "🌐 Kabinet"]))
async def open_cabinet(message: Message) -> None:
    """Send an inline button that opens the Mini App via WebAppInfo."""
    if not settings.miniapp_url:
        await message.answer("⚠️ Mini App URL не настроен. Свяжитесь с @khaetov_000")
        return

    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        lang = user.language_code or "ru"
    finally:
        db.close()

    btn_label = "🌐 Открыть кабинет" if lang == "ru" else "🌐 Kabinetni ochish"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=btn_label,
            web_app=WebAppInfo(url=settings.miniapp_url),
        )
    ]])

    text = i18n.get("open_cabinet", lang)
    await message.answer(text, reply_markup=keyboard)
