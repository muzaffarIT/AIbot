import os

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv

from bot.keyboards.language import language_keyboard
from bot.keyboards.main_menu import main_menu_keyboard
from bot.keyboards.webapp import open_cabinet_keyboard
from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from shared.utils.i18n import I18n

load_dotenv()

router = Router()
i18n = I18n()

MINIAPP_URL = os.getenv("MINIAPP_URL", "http://localhost:3000")


@router.message(F.text == "/start")
async def cmd_start(message: Message) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

        await message.answer(
            i18n.t(user.language_code, "start.choose_language"),
            reply_markup=language_keyboard(),
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("lang:"))
async def process_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":")[1]

    db = get_db_session()
    try:
        user_service = UserService(db)
        user_service.set_user_language(callback.from_user.id, lang)

        await callback.message.answer(
            i18n.t(lang, "start.welcome"),
            reply_markup=main_menu_keyboard(lang),
        )
        await callback.answer()
    finally:
        db.close()


@router.message()
async def fallback_menu(message: Message) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        lang = user_service.get_user_language(message.from_user.id)

        if message.text == i18n.t(lang, "menu.open_cabinet"):
            await message.answer(
                i18n.t(lang, "menu.open_cabinet"),
                reply_markup=open_cabinet_keyboard(
                    MINIAPP_URL,
                    i18n.t(lang, "menu.open_cabinet"),
                ),
            )
            return

        if message.text == i18n.t(lang, "menu.language"):
            await message.answer(
                i18n.t(lang, "start.choose_language"),
                reply_markup=language_keyboard(),
            )
            return

        await message.answer(i18n.t(lang, "common.soon"))
    finally:
        db.close()
