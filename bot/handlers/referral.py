"""
Bilingual /referral handler and referral notification utility.
"""
import logging
from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from backend.core.config import settings
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()
logger = logging.getLogger(__name__)


@router.message(Command("referral"))
async def referral_cmd(message: Message, bot: Bot) -> None:
    await _send_referral_info(message.from_user.id, message, bot)


@router.callback_query(F.data == "menu_referral")
async def referral_callback(callback: CallbackQuery, bot: Bot) -> None:
    await _send_referral_info(callback.from_user.id, callback.message, bot)
    await callback.answer()


# Handle reply keyboard button
@router.message(F.text.in_(["👥 Партнёрам", "👥 Hamkorlik"]))
async def referral_reply_btn(message: Message, bot: Bot) -> None:
    await _send_referral_info(message.from_user.id, message, bot)


async def _send_referral_info(telegram_id: int, message, bot: Bot) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_or_create_user(
            telegram_user_id=telegram_id,
            username=getattr(message, "from_user", None) and message.from_user.username or None,
            first_name=None,
            last_name=None,
        )
        lang = user.language_code or "ru"

        ref_code = user.referral_code or ""
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{ref_code}"

        ref_count = user_service.get_referral_count(user.id)
        earnings = getattr(user, "referral_earnings", 0) or 0

        text = i18n.t(lang, "referral.title",
                      link=ref_link, count=ref_count, earnings=earnings)

        share_text = (f"BATIR AI — sun'iy intellekt yordamida rasm va video yarating! +10 kredit sovg'a 🎁"
                      if lang == "uz" else
                      f"BATIR AI — создавай картинки и видео с помощью ИИ! +10 кредитов в подарок 🎁")
        share_url = f"https://t.me/share/url?url={ref_link}&text={share_text}"

        await message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=i18n.t(lang, "referral.btn.share"),
                    url=share_url,
                )],
                [InlineKeyboardButton(
                    text=i18n.t(lang, "referral.btn.copy"),
                    callback_data=f"copy_ref:{ref_code}",
                )],
            ]),
            parse_mode="HTML",
        )
    finally:
        db.close()


@router.callback_query(F.data.startswith("copy_ref:"))
async def copy_ref_callback(callback: CallbackQuery, bot: Bot) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        lang = (user.language_code if user else None) or "ru"

        bot_info = await bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{callback.data.split(':')[1]}"

        msg = f"🔗 Sizning havolangiz:\n{ref_link}" if lang == "uz" else f"🔗 Твоя ссылка:\n{ref_link}"
        await callback.message.answer(msg)
        await callback.answer("✅")
    finally:
        db.close()


async def notify_referrer_on_purchase(bot: Bot, referred_user_id: int) -> None:
    """Called when a referred user (database internal ID) makes their first purchase."""
    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        referred = user_service.repo.get_by_id(referred_user_id)
        if not referred or not referred.referred_by_telegram_id:
            logger.info(f"[Referral] User {referred_user_id} has no referrer.")
            return

        referrer = user_service.get_user_by_telegram_id(referred.referred_by_telegram_id)
        if not referrer:
            logger.warning(f"[Referral] Referrer telegram_id={referred.referred_by_telegram_id} not found.")
            return

        lang = referrer.language_code or "ru"
        bonus = settings.referral_bonus_referrer

        # Add credits to referrer
        balance_service.add_credits(referrer.id, bonus, "referral_purchase_bonus")
        
        # Update stats
        referrer.referral_earnings = (referrer.referral_earnings or 0) + bonus
        referred.referral_bonus_paid = True
        db.commit()

        # Notify
        RU = text = i18n.t("ru", "referral.purchase_notify", default="🎉 Твой реферал совершил первую покупку!\n💰 Начислено кредитов!")
        UZ = i18n.t("uz", "referral.purchase_notify", default="🎉 Referalingiz birinchi xaridni qildi!\n💰 Kredit berildi!")
        
        try:
            await bot.send_message(referrer.telegram_user_id, RU if lang == "ru" else UZ)
        except Exception as e:
            logger.error(f"[Referral] Failed to send notification message to {referrer.telegram_user_id}: {e}")
            
        logger.info(f"[Referral] Awarded {bonus} to referrer {referrer.telegram_user_id} for user {referred.telegram_user_id} purchase.")
    except Exception as e:
        logger.error(f"[Referral] notify_referrer_on_purchase error: {e}")
    finally:
        db.close()

