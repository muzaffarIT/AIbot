from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command, CommandStart

from bot.keyboards.main_menu import main_inline_keyboard
from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from backend.core.config import settings

router = Router()

FREE_WELCOME_CREDITS = settings.welcome_credits


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        # Check referral deep link: /start ref_XXXXXXXX
        ref_code: str | None = None
        args = message.text.split(" ", 1)
        if len(args) > 1 and args[1].startswith("ref_"):
            ref_code = args[1][4:]  # strip "ref_"

        # Detect if user is new before calling get_or_create
        existing = user_service.get_user_by_telegram_id(message.from_user.id)
        is_new = existing is None

        user = user_service.get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )

        # Apply referral if new user and valid code
        if is_new and ref_code:
            referrer = user_service.get_user_by_referral_code(ref_code)
            if referrer and referrer.telegram_user_id != user.telegram_user_id:
                user_service.set_referred_by(user.id, referrer.telegram_user_id)

        # Welcome bonus for new users
        if is_new:
            balance_service.add_credits(user.id, FREE_WELCOME_CREDITS, "welcome_bonus")
            db.commit()

        credits = balance_service.get_balance_value(user.id)
        name = user.first_name or message.from_user.username or "друг"

        # First: remove any old reply keyboard
        await message.answer("👋", reply_markup=ReplyKeyboardRemove())

        if is_new:
            text = (
                f"👋 Привет, <b>{name}</b>!\n"
                f"Добро пожаловать в <b>BATIR AI</b> 🤖\n\n"
                f"🎁 Тебе начислено <b>{FREE_WELCOME_CREDITS}</b> бесплатных кредитов!\n"
                f"Попробуй создать свой первый нейроарт прямо сейчас.\n\n"
                f"💰 Баланс: <b>{credits}</b> кредитов\n\n"
                f"Используя бота, ты принимаешь /terms"
            )
        else:
            text = (
                f"👋 Привет, <b>{name}</b>!\n"
                f"Рад снова видеть тебя в <b>BATIR AI</b> 🤖\n\n"
                f"💰 Баланс: <b>{credits}</b> кредитов\n\n"
                f"Выбери действие:"
            )

        await message.answer(text, reply_markup=main_inline_keyboard(), parse_mode="HTML")
    finally:
        db.close()
