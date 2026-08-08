"""
Daily bonus and streak system.
"""
import logging
from aiogram import F, Router, Bot
from aiogram.types import Message
from aiogram.filters import Command

from bot.keyboards.reply_menu import main_reply_keyboard
from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)
router = Router()
i18n = I18n()

# Streak Badges
STREAK_BADGES = {
    7: "Неделя творчества 🎨",
    30: "Месячный мастер 👑",
}

STREAK_BADGES_UZ = {
    7: "Bir hafta ijodkor 🎨",
    30: "Oylik usta 👑",
}

@router.message(Command("daily"))
async def daily_cmd(message: Message, bot: Bot) -> None:
    await _handle_daily_bonus(message.from_user.id, message, bot)

# Handle reply keyboard "☀️ Бонус" / "☀️ Bonus"
@router.message(F.text.in_(["☀️ Бонус", "☀️ Bonus"]))
async def daily_reply_btn(message: Message, bot: Bot) -> None:
    await _handle_daily_bonus(message.from_user.id, message, bot)

async def _handle_daily_bonus(telegram_id: int, message: Message, bot: Bot) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(telegram_id)
        if not user:
            return

        lang = user.language_code or "ru"
        result = user_service.claim_daily_bonus(user.id)

        if not result["success"]:
            if result.get("error") == "already_claimed":
                text = i18n.t(lang, "daily.already_claimed",
                             hours=result["hours"], minutes=result["minutes"], streak=result["streak"])
                await message.answer(text, reply_markup=main_reply_keyboard(lang))
                return
            return

        streak = result["streak"]
        credits = result["credits"]
        balance = result["balance"]

        # Tomorrow's reward is the next step of the streak (capped at 10).
        # Showing it drives day-2 retention — the whole point of a daily bonus.
        tomorrow_credits = min(10, streak + 1)

        if lang == "uz":
            text = (
                f"🎉 <b>Bonus olindi!</b>\n\n"
                f"➕ Hisoblandi: <b>{credits} kredit</b>\n"
                f"🔥 Ketma-ketlik: <b>{streak} kun</b>\n"
                f"💰 Balans: <b>{balance} kredit</b>\n\n"
                f"📅 Ertaga: <b>+{tomorrow_credits} kredit</b> — ketma-ketlikni uzatma! ⏰"
            )
        else:
            text = (
                f"🎉 <b>Бонус забран!</b>\n\n"
                f"➕ Начислено: <b>{credits} кредитов</b>\n"
                f"🔥 Серия: <b>{streak} дн.</b>\n"
                f"💰 Баланс: <b>{balance} кредитов</b>\n\n"
                f"📅 Завтра: <b>+{tomorrow_credits} кредитов</b> — не прерывай серию! ⏰"
            )

        # Badge message for milestone streaks
        badge = (STREAK_BADGES_UZ if lang == "uz" else STREAK_BADGES).get(streak)
        if badge:
            text += f"\n\n" + i18n.t(lang, "daily.streak_badge", badge=badge)

        # Notify about achievements earned during streak claim
        newly_earned = result.get("newly_earned", [])
        if newly_earned:
            for ach, bonus in newly_earned:
                name = ach.name_uz if lang == "uz" else ach.name_ru
                text += (
                    f"\n\n🏆 <b>Yangi yutuq!</b>\n{ach.emoji} <b>{name}</b> — +{bonus} кр. 🎉"
                    if lang == "uz" else
                    f"\n\n🏆 <b>Новое достижение!</b>\n{ach.emoji} <b>{name}</b> — +{bonus} кр. 🎉"
                )

        from aiogram.exceptions import TelegramForbiddenError
        try:
            await message.answer(text, reply_markup=main_reply_keyboard(lang), parse_mode="HTML")
            logger.info(f"[Daily] user={telegram_id} claimed streak={streak} credits={credits}")
        except TelegramForbiddenError:
            logger.warning(f"User blocked bot: {telegram_id}")
            return

    finally:
        db.close()
