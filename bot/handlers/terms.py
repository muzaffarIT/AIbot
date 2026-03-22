"""
Bilingual /terms handler.
"""
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()


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



@router.message(Command("terms"))
async def show_terms_cmd(message: Message) -> None:
    lang = _get_lang(message.from_user.id)
    btn_text = "✅ Qabul qilaman" if lang == "uz" else "✅ Принимаю"
    await message.answer(
        i18n.t(lang, "terms.text"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data="terms_accept")]
        ]),
    )


@router.callback_query(F.data == "menu_terms")
async def show_terms_callback(callback: CallbackQuery) -> None:
    lang = _get_lang(callback.from_user.id)
    btn_text = "✅ Qabul qilaman" if lang == "uz" else "✅ Принимаю"
    await callback.message.answer(
        i18n.t(lang, "terms.text"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, callback_data="terms_accept")]
        ]),
    )
    await callback.answer()


@router.callback_query(F.data == "terms_accept")
async def accept_terms(callback: CallbackQuery) -> None:
    lang = _get_lang(callback.from_user.id)
    msg = "✅ Qabul qildi! Raxmat." if lang == "uz" else "✅ Принято! Спасибо."
    await callback.answer(msg, show_alert=False)
