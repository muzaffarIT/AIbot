"""
Bilingual /help handler.
"""
import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()
logger = logging.getLogger(__name__)


def _get_lang(telegram_id: int) -> str:
    db = get_db_session()
    lang = "ru"
    try:
        user = UserService(db).get_user_by_telegram_id(telegram_id)
        if user and user.language_code:
            lang = user.language_code
    finally:
        db.close()
    return lang



@router.message(Command("help"))
async def show_help_cmd(message: Message) -> None:
    lang = _get_lang(message.from_user.id)
    await message.answer(
        i18n.t(lang, "help.text"),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "menu_help")
async def show_help_callback(callback: CallbackQuery) -> None:
    lang = _get_lang(callback.from_user.id)
    await callback.message.answer(i18n.t(lang, "help.text"), parse_mode="HTML")
    await callback.answer()


# Handle reply keyboard button "❓ Помощь" / "❓ Yordam"
@router.message(F.text.in_(["❓ Помощь", "❓ Yordam"]))
async def help_reply_btn(message: Message) -> None:
    lang = _get_lang(message.from_user.id)
    await message.answer(i18n.t(lang, "help.text"), parse_mode="HTML")
