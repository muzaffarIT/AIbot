from aiogram import F, Router
from aiogram.types import Message

from backend.services.generation_service import GenerationService
from backend.services.user_service import UserService
from bot.services.db_session import get_db_session
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()

JOBS_TRIGGERS = {
    "/jobs",
    i18n.t("ru", "menu.jobs"),
    i18n.t("uz", "menu.jobs"),
}


def _format_job_line(job) -> str:
    return f"#{job.id} - {job.provider} - {job.status} - {job.credits_reserved} cr"


@router.message(F.text.in_(JOBS_TRIGGERS))
async def show_jobs(message: Message) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        generation_service = GenerationService(db)

        user = user_service.get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        jobs = generation_service.get_user_jobs(user.telegram_user_id, limit=5)

        if not jobs:
            await message.answer(i18n.t(user.language_code, "jobs.history.empty"))
            return

        lines = [i18n.t(user.language_code, "jobs.history.title")]
        for job in jobs:
            lines.append(_format_job_line(job))
            if job.result_url:
                lines.append(job.result_url)
            elif job.error_message:
                lines.append(job.error_message)

        await message.answer("\n".join(lines))
    finally:
        db.close()
