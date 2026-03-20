"""
Daily bonus and streak system.
"""
import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from bot.keyboards.reply_menu import main_reply_keyboard, REPLY_BUTTON_ACTIONS
from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)
router = Router()
i18n = I18n()

# Streak → base bonus credits
STREAK_BONUSES = {
    1: 3,
    3: 8,   # 3 + 5 bonus
    7: 18,  # 3 + 15 bonus + badge
    14: 28, # 3 + 25 bonus
    30: 53, # 3 + 50 bonus + VIP
}

STREAK_BADGES = {
    7: "Неделя творчества 🎨",
    30: "Месячный мастер 👑",
}

STREAK_BADGES_UZ = {
    7: "Bir hafta ijodkor 🎨",
    30: "Oylik usta 👑",
}


def _get_daily_credits(streak: int) -> int:
    """Returns credits for the given streak day."""
    for threshold in sorted(STREAK_BONUSES.keys(), reverse=True):
        if streak >= threshold:
            return STREAK_BONUSES[threshold]
    return 3


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
        balance_service = BalanceService(db)

        user = user_service.get_or_create_user(
            telegram_user_id=telegram_id,
            username=message.from_user.username if hasattr(message.from_user, "username") else None,
            first_name=getattr(message.from_user, "first_name", None),
            last_name=getattr(message.from_user, "last_name", None),
        )
        lang = user.language_code or "ru"

        now = datetime.now(timezone.utc)
        last_claim = getattr(user, "last_daily_claim", None)
        streak = getattr(user, "daily_streak", 0) or 0

        if last_claim and last_claim.tzinfo is None:
            last_claim = last_claim.replace(tzinfo=timezone.utc)

        if last_claim:
            hours_since = (now - last_claim).total_seconds() / 3600
            if hours_since < 24:
                # Already claimed
                next_in = timedelta(hours=24) - (now - last_claim)
                hours_left = int(next_in.total_seconds() // 3600)
                mins_left = int((next_in.total_seconds() % 3600) // 60)
                text = i18n.t(lang, "daily.already_claimed",
                              hours=hours_left, minutes=mins_left, streak=streak)
                await message.answer(text)
                return

            # Check if streak is broken (more than 48h since last claim → reset)
            if hours_since > 48:
                streak = 0

        # Award bonus
        streak += 1
        credits = _get_daily_credits(streak)

        balance = balance_service.add_credits(user.id, credits, "daily_bonus")
        user.last_daily_claim = now
        user.daily_streak = streak
        if streak > (getattr(user, "max_streak", 0) or 0):
            user.max_streak = streak
        db.commit()

        text = i18n.t(lang, "daily.claimed", credits=credits, streak=streak, balance=balance)

        # Badge message for milestone streaks
        badge = (STREAK_BADGES_UZ if lang == "uz" else STREAK_BADGES).get(streak)
        if badge:
            text += f"\n\n" + i18n.t(lang, "daily.streak_badge", badge=badge)

        await message.answer(text, reply_markup=main_reply_keyboard(lang))
        logger.info(f"[Daily] user={telegram_id} claimed streak={streak} credits={credits}")

    finally:
        db.close()
