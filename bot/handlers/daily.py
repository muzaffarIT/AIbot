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
                await message.answer(text)
                return
            return

        # result: {"success": True, "credits": credits, "streak": streak, "balance": balance}
        text = i18n.t(lang, "daily.claimed", 
                      credits=result["credits"], 
                      streak=result["streak"], 
                      balance=result["balance"])

        # Badge message for milestone streaks
        streak = result["streak"]
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
            logger.info(f"[Daily] user={telegram_id} claimed streak={streak} credits={result['credits']}")
        except TelegramForbiddenError:
            logger.warning(f"User blocked bot: {telegram_id}")
            return

    finally:
        db.close()
