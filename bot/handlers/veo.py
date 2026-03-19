from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from backend.services.generation_service import GenerationService
from backend.services.user_service import UserService
from bot.services.db_session import get_db_session
from bot.states.veo_states import VeoStates
from shared.enums.providers import AIProvider
from shared.utils.i18n import I18n
from bot.services.progress import track_generation_progress
import asyncio

router = Router()
i18n = I18n()

TRIGGERS = {
    i18n.t("ru", "menu.create_video"),
    i18n.t("uz", "menu.create_video"),
}


@router.message(F.text.in_(TRIGGERS))
async def ask_for_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(VeoStates.waiting_for_prompt)
    await message.answer("Отправьте prompt для генерации видео через Veo.")


@router.message(VeoStates.waiting_for_prompt)
async def create_veo_job(message: Message, state: FSMContext) -> None:
    prompt = message.text or ""
    if len(prompt) < 3 or len(prompt) > 500:
        await message.answer("❌ Длина промпта должна быть от 3 до 500 символов. Пожалуйста, отправьте другой промпт.")
        return

    db = get_db_session()
    try:
        user = UserService(db).get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        job = GenerationService(db).create_job_for_user(
            telegram_user_id=user.telegram_user_id,
            provider=AIProvider.VEO,
            prompt=message.text or "",
        )

        lines = [
            "⏳ Задача на генерацию видео через Veo создана и отправлена в очередь.",
            f"ID: {job.id}",
        ]
        msg = await message.answer("\n".join(lines))
        
        # Start background progress tracking
        asyncio.create_task(
            track_generation_progress(message.bot, message.chat.id, msg.message_id, job.id)
        )
    except ValueError as exc:
        await message.answer(str(exc))
    finally:
        await state.clear()
        db.close()
