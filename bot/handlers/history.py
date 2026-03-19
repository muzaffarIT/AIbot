from aiogram import F, Router
from aiogram.types import Message, CallbackQuery

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.generation_service import GenerationService
from shared.utils.i18n import I18n

from backend.models.generation_job import GenerationJob
from shared.enums.job_status import JobStatus

router = Router()
i18n = I18n()

@router.message(F.text == "/history")
async def cmd_history(message: Message) -> None:
    await send_history(message)

# Also handle the inline button from welcome menu
@router.callback_query(F.data == "history_cmd")
async def callback_history(callback: CallbackQuery) -> None:
    await send_history(callback.message, callback.from_user.id)
    await callback.answer()

async def send_history(message: Message, telegram_id: int = None) -> None:
    db = get_db_session()
    try:
        user_id = telegram_id or message.from_user.id
        user_service = UserService(db)
        gen_service = GenerationService(db)
        
        user = user_service.get_or_create_user(
            telegram_user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        lang = user.language_code or "ru"

        # Fetch recent 5 generation jobs
        jobs = db.query(GenerationJob).filter(
            GenerationJob.user_id == user.id
        ).order_by(GenerationJob.created_at.desc()).limit(5).all()

        if not jobs:
            await message.answer(i18n.t(lang, "jobs.history.empty"))
            return

        lines = [i18n.t(lang, "jobs.history.title"), ""]
        for j in jobs:
            status_emoji = {
                JobStatus.COMPLETED: "✅",
                JobStatus.FAILED: "❌",
                JobStatus.PROCESSING: "⏳",
                JobStatus.PENDING: "🕒",
                JobStatus.CANCELLED: "🚫"
            }.get(j.status, "❓")
            
            prompt_trunc = j.prompt[:30] + "..." if len(j.prompt) > 30 else j.prompt
            lines.append(f"{status_emoji} <b>{j.provider}</b>")
            lines.append(f"└ <i>{prompt_trunc}</i>")
            
        await message.answer("\n".join(lines), parse_mode="HTML")
    finally:
        db.close()
