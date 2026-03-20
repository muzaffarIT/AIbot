import asyncio
from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from backend.services.generation_service import GenerationService
from backend.services.user_service import UserService
from bot.services.db_session import get_db_session
from bot.states.nanobanana_states import NanoBananaStates
from shared.enums.providers import AIProvider
from shared.utils.i18n import I18n
from bot.services.progress import track_generation_progress

router = Router()
i18n = I18n()

TRIGGERS = {
    i18n.t("ru", "menu.generate_image"),
    i18n.t("uz", "menu.generate_image"),
}


@router.message(NanoBananaStates.waiting_for_prompt, F.text)
async def create_nanobanana_job(message: Message, state: FSMContext) -> None:
    prompt = message.text or ""
    if len(prompt) < 3 or len(prompt) > 500:
        await message.answer("❌ Длина промпта: от 3 до 500 символов.")
        return

    state_data = await state.get_data()
    source_image_url = state_data.get("source_image_url")

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
            provider=AIProvider.NANO_BANANA,
            prompt=prompt,
            source_image_url=source_image_url,
        )
        mode = "Image-to-Image" if source_image_url else "Text-to-Image"
        msg = await message.answer(
            f"⏳ <b>Nano Banana</b> ({mode}) — задача #{job.id} в очереди.\n\n"
            "🖼 Картинка будет готова примерно через 30-60 секунд!",
            parse_mode="HTML",
        )
        asyncio.create_task(
            track_generation_progress(message.bot, message.chat.id, msg.message_id, job.id)
        )
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
    finally:
        await state.clear()
        db.close()
