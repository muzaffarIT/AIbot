from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from backend.services.generation_service import GenerationService
from backend.services.user_service import UserService
from bot.services.db_session import get_db_session
from bot.states.kling_states import KlingStates
from shared.enums.providers import AIProvider
from shared.utils.i18n import I18n
from bot.services.progress import track_generation_progress
import asyncio

router = Router()
i18n = I18n()

TRIGGERS = {
    i18n.t("ru", "menu.animate_image"),
    i18n.t("uz", "menu.animate_image"),
}


@router.message(F.text.in_(TRIGGERS))
async def ask_for_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(KlingStates.waiting_for_prompt)
    await message.answer("Отправьте prompt для анимации через Kling Motion.")


@router.message(KlingStates.waiting_for_prompt)
async def create_kling_job(message: Message, state: FSMContext) -> None:
    prompt = message.text or ""
    if len(prompt) < 3 or len(prompt) > 500:
        await message.answer("❌ Длина промпта должна быть от 3 до 500 символов. Пожалуйста, отправьте другой промпт.")
        return

    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(message.from_user.id)
        if not user:
            return
        lang = user.language_code or "ru"
        
        from bot.services.translator import translate_prompt
        translated = translate_prompt(prompt)
        await state.update_data(prompt=translated, original_prompt=prompt)
        await state.set_state(KlingStates.waiting_for_quality)
        
        from bot.keyboards.quality_menu import get_quality_keyboard
        await message.answer(
            i18n.t(lang, "quality.select"),
            reply_markup=get_quality_keyboard("kling", lang)
        )
    finally:
        db.close()
