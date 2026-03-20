import os

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from dotenv import load_dotenv

from bot.keyboards.main_menu import main_inline_keyboard
from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from shared.utils.i18n import I18n

load_dotenv()

router = Router()
i18n = I18n()


@router.message(F.text == "/start")
async def cmd_start(message: Message) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        user = user_service.get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        credits = balance_service.get_balance_value(user.id)
        name = user.first_name or message.from_user.username or "друг"

        text = (
            f"👋 Привет, <b>{name}</b>!\n"
            f"Добро пожаловать в <b>BATIR AI</b>.\n"
            f"У тебя <b>{credits}</b> кредитов.\n\n"
            f"Выбери действие:"
        )

        await message.answer(text, reply_markup=main_inline_keyboard(), parse_mode="HTML")
    finally:
        db.close()
