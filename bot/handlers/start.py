from aiogram import Router, Bot, types
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError

from bot.keyboards.reply_menu import main_reply_keyboard
from bot.keyboards.main_menu import main_inline_keyboard
from bot.handlers.onboarding import start_onboarding
from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from backend.services.settings_service import SettingsService
from backend.core.config import settings
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, state: FSMContext) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        # Check deep link param
        ref_code: str | None = None
        args = message.text.split(" ", 1) if message.text else [""]
        deep_link_arg = args[1] if len(args) > 1 else ""

        if deep_link_arg.startswith("ref_"):
            ref_code = deep_link_arg[4:]  # strip "ref_"
        elif deep_link_arg == "uzs_topup":
            pass  # handled after user setup below

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
                
                # Referrer gets 5 credits for the new registration
                balance_service.add_credits(referrer.id, 5, "referral_registration_bonus")
                db.commit()
                
                # Notify referrer
                try:
                    ref_lang = referrer.language_code or "ru"
                    ref_notify = (
                        f"👥 <b>Yangi referal!</b>\n\n"
                        f"Havolangiz orqali yangi foydalanuvchi ro'yxatdan o'tdi.\n"
                        f"Hisobingizga <b>+5</b> kredit qo'shildi 🎁\n\n"
                        f"Hamkorlik dasturi: har bir to'ldirishdan 10% komissiya olasiz!"
                        if ref_lang == "uz" else
                        f"👥 <b>Новый реферал!</b>\n\n"
                        f"По вашей ссылке зарегистрировался новый пользователь.\n"
                        f"На ваш счёт зачислено <b>+5</b> кредитов 🎁\n\n"
                        f"Партнёрская программа: получайте 10% с каждого пополнения друга!"
                    )
                    await bot.send_message(
                        referrer.telegram_user_id,
                        ref_notify,
                        parse_mode="HTML"
                    )
                except:
                    pass

        # Welcome bonus for new users
        if is_new:
            settings_service = SettingsService(db)
            welcome_credits = settings_service.get_int("welcome_credits", settings.welcome_credits)
            balance_service.add_credits(user.id, welcome_credits, "welcome_bonus")
            db.commit()

        # Onboarding trigger (Block 2)
        if not user.onboarding_completed:
            await state.clear()
            await start_onboarding(message, state, lang)
            return

        name = user.first_name or message.from_user.username or "друг"

        # Remove any lingering old reply keyboards
        try:
            await message.answer("👋", reply_markup=ReplyKeyboardRemove())
        except TelegramForbiddenError:
            import logging
            logging.warning(f"User {message.from_user.id} blocked bot")
            return
        except Exception as e:
            import logging
            logging.error(f"Start error: {e}")
            return

        if lang == "uz":
            text = (
                f"Xush kelibsiz, <b>{name}</b> 👋\n\n"
                f"<b>HARF AI</b> — sun'iy intellekt bilan rasm va video yarating.\n"
                f"━━━━━━━━━━━━━━\n"
                f"Quyidagi menyudan foydalaning 👇"
            )
        else:
            text = (
                f"Добро пожаловать, <b>{name}</b> 👋\n\n"
                f"<b>HARF AI</b> — создавайте изображения и видео с помощью нейросетей.\n"
                f"━━━━━━━━━━━━━━\n"
                f"Используйте меню ниже 👇"
            )

        # Send reply keyboard as main navigation
        try:
            await message.answer(
                text,
                reply_markup=main_reply_keyboard(lang),
                parse_mode="HTML",
            )
        except TelegramForbiddenError:
            return

        # Deep link: open UZS top-up menu directly
        if deep_link_arg == "uzs_topup":
            from bot.handlers.callbacks import send_uzs_topup_menu
            try:
                await send_uzs_topup_menu(message.answer, lang)
            except Exception:
                pass

    finally:
        db.close()
