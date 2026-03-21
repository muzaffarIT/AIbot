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


from bot.keyboards.quality_menu import get_quality_keyboard


@router.message(NanoBananaStates.waiting_for_prompt, F.text)
async def handle_nanobanana_prompt(message: Message, state: FSMContext) -> None:
    prompt = message.text or ""
    if len(prompt) < 3 or len(prompt) > 500:
        await message.answer("❌ Длина промпта: от 3 до 500 символов.")
        return

    db = next(get_db_session())
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(message.from_user.id)
        lang = user.language_code or "ru"
        
        await state.update_data(prompt=prompt)
        await state.set_state(NanoBananaStates.waiting_for_quality)
        
        await message.answer(
            i18n.t(lang, "quality.select"),
            reply_markup=get_quality_keyboard("nano_banana", lang)
        )
    finally:
        db.close()
