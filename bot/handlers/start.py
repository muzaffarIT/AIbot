from aiogram import Router, Bot
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import CommandStart

from bot.keyboards.reply_menu import main_reply_keyboard
from bot.keyboards.main_menu import main_inline_keyboard
from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from backend.core.config import settings
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()


@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        # Check referral deep link: /start ref_XXXXXXXX
        ref_code: str | None = None
        args = message.text.split(" ", 1) if message.text else [""]
        if len(args) > 1 and args[1].startswith("ref_"):
            ref_code = args[1][4:]  # strip "ref_"

        # Detect if user is new
        existing = user_service.get_user_by_telegram_id(message.from_user.id)
        is_new = existing is None

        user = user_service.get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        lang = user.language_code or "ru"

        # Apply referral if new user and valid code
        if is_new and ref_code:
            referrer = user_service.get_user_by_referral_code(ref_code)
            if referrer and referrer.telegram_user_id != user.telegram_user_id:
                user_service.set_referred_by(user.id, referrer.telegram_user_id)
                # New user gets extra 10 credits (on top of welcome bonus)
                balance_service.add_credits(user.id, settings.referral_bonus_new_user, "referral_welcome")

        # Welcome bonus for new users
        if is_new:
            balance_service.add_credits(user.id, settings.welcome_credits, "welcome_bonus")
            db.commit()

        credits = balance_service.get_balance_value(user.id)
        name = user.first_name or message.from_user.username or "друг"

        # Remove any lingering old reply keyboards
        await message.answer("👋", reply_markup=ReplyKeyboardRemove())

        if is_new:
            text = i18n.t(lang, "onboarding.step1", name=name)
        else:
            if lang == "uz":
                text = (
                    f"👋 Qaytib keldingiz, <b>{name}</b>!\n\n"
                    f"💰 Balansingiz: <b>{credits}</b> kredit\n\n"
                    f"Nima qilamiz?"
                )
            else:
                text = (
                    f"👋 С возвращением, <b>{name}</b>!\n\n"
                    f"💰 Баланс: <b>{credits}</b> кредитов\n\n"
                    f"Что делаем?"
                )

        # Send reply keyboard as main navigation
        await message.answer(
            text,
            reply_markup=main_reply_keyboard(lang),
            parse_mode="HTML",
        )

        # For new users: run onboarding in background
        if is_new:
            import asyncio
            from bot.handlers.onboarding import run_onboarding
            asyncio.create_task(run_onboarding(bot, message.chat.id, name, lang))

    finally:
        db.close()
