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
import logging

logger = logging.getLogger(__name__)
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
    logger.info(f"[KLING] Got prompt: {prompt[:50]}")
    if len(prompt) < 3 or len(prompt) > 500:
        await message.answer("❌ Длина промпта должна быть от 3 до 500 символов.")
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

        state_data = await state.get_data()
        cost    = state_data.get("quality_cost")
        payload = state_data.get("quality_payload")

        if cost is None:
            # Fallback (photo flow): show quality keyboard
            await state.update_data(prompt=translated, original_prompt=prompt)
            await state.set_state(KlingStates.waiting_for_quality)
            from bot.keyboards.quality_menu import get_quality_keyboard
            await message.answer(
                i18n.t(lang, "quality.select"),
                reply_markup=get_quality_keyboard("kling", lang)
            )
            return

        # Quality already selected → create job immediately
        from backend.services.generation_service import GenerationService
        from bot.services.progress import track_generation_progress
        job = GenerationService(db).create_job_for_user(
            telegram_user_id=user.telegram_user_id,
            provider=AIProvider.KLING,
            prompt=translated,
            original_prompt=prompt,
            source_image_url=state_data.get("source_image_url"),
            job_payload=payload,
            credits=cost,
        )
        msg = await message.answer(
            "⏳ <b>Kling Motion</b> — задача принята.\n\n"
            f"💰 Списано: {cost} кр.\n🔄 Готовим результат... (~3–5 мин)",
            parse_mode="HTML",
        )
        asyncio.create_task(
            track_generation_progress(message.bot, message.chat.id, msg.message_id, job.id)
        )
        await state.clear()
    except ValueError as exc:
        await message.answer(f"❌ {exc}")
    finally:
        db.close()
