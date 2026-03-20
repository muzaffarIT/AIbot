from aiogram import F, Router, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from backend.core.config import settings

router = Router()


@router.message(Command("referral"))
async def referral_info_cmd(message: Message, bot: Bot) -> None:
    await _send_referral_info(message.from_user.id, message, bot)


@router.callback_query(F.data == "menu_referral")
async def referral_info_callback(callback: CallbackQuery, bot: Bot) -> None:
    await _send_referral_info(callback.from_user.id, callback.message, bot)
    await callback.answer()


async def _send_referral_info(telegram_id: int, message: Message, bot: Bot) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)
        user = user_service.get_or_create_user(
            telegram_user_id=telegram_id,
            username=None,
            first_name=None,
            last_name=None,
        )

        bot_info = await bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user.referral_code}"

        referral_count = user_service.get_referral_count(user.id)
        earned = user.referral_earnings

        text = (
            f"👥 <b>Партнёрская программа BATIR AI</b>\n\n"
            f"Приглашай друзей и получай <b>20 кредитов</b>\n"
            f"за каждого, кто совершит первую покупку!\n\n"
            f"Твой друг тоже получает <b>10 бонусных кредитов</b> при регистрации.\n\n"
            f"🔗 Твоя реферальная ссылка:\n"
            f"<code>{ref_link}</code>\n\n"
            f"📊 Статистика:\n"
            f"👤 Приглашено: <b>{referral_count}</b> чел.\n"
            f"💰 Заработано: <b>{earned}</b> кредитов"
        )

        share_url = f"https://t.me/share/url?url={ref_link}&text=Попробуй+BATIR+AI+—+нейросети+для+генерации+арта+и+видео!"

        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=share_url)],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start_menu")],
            ]),
        )
    finally:
        db.close()


async def notify_referrer_on_purchase(bot: Bot, referrer_telegram_id: int, bonus: int = 20) -> None:
    """Called when a referred user makes their first purchase."""
    try:
        db = get_db_session()
        try:
            referrer = UserService(db).get_user_by_telegram_id(referrer_telegram_id)
            if not referrer:
                return
            balance_service = BalanceService(db)
            balance_service.add_credits(referrer.id, bonus, "referral_bonus")
            # Update earnings counter
            referrer.referral_earnings = (referrer.referral_earnings or 0) + bonus
            db.commit()
        finally:
            db.close()

        await bot.send_message(
            referrer_telegram_id,
            f"🎉 Твой реферал совершил первую покупку!\n"
            f"💰 +{bonus} кредитов зачислено на баланс!",
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to notify referrer {referrer_telegram_id}: {e}")
