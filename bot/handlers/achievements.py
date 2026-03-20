"""
Achievements handler — /achievements command.
"""
from aiogram import F, Router
from aiogram.types import Message
from aiogram.filters import Command

from bot.services.db_session import get_db_session
from bot.services.achievements import ACHIEVEMENTS, ACHIEVEMENT_MAP
from backend.services.user_service import UserService
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()


@router.message(Command("achievements"))
async def show_achievements_cmd(message: Message) -> None:
    await _show_achievements(message.from_user.id, message)


async def _show_achievements(telegram_id: int, message: Message) -> None:
    db = get_db_session()
    try:
        from sqlalchemy import select
        from backend.models.achievement import Achievement

        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(telegram_id)
        lang = (user.language_code if user else None) or "ru"

        earned_rows = db.execute(
            select(Achievement).where(
                Achievement.user_id == (user.id if user else -1)
            )
        ).scalars().all()

        earned_map = {r.achievement_code: r.earned_at for r in earned_rows}
        total = len(ACHIEVEMENTS)
        count = len(earned_map)

        title = i18n.t(lang, "achievements.title", count=count, total=total)
        lines = [title, ""]

        for ach in ACHIEVEMENTS:
            name = ach.name_uz if lang == "uz" else ach.name_ru
            if ach.code in earned_map:
                earned_at = earned_map[ach.code].strftime("%d.%m.%Y")
                lines.append(f"✅ {ach.emoji} <b>{name}</b> — +{ach.bonus_credits} кр.  <i>({earned_at})</i>")
            else:
                lines.append(f"🔒 {ach.emoji} {name} — +{ach.bonus_credits} кр.")

        await message.answer("\n".join(lines), parse_mode="HTML")
    finally:
        db.close()
