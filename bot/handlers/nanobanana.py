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
from bot.keyboards.quality_menu import get_quality_keyboard

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

    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(message.from_user.id)
        lang = user.language_code or "ru"

        from bot.services.translator import translate_prompt
        translated = translate_prompt(prompt)

        state_data = await state.get_data()
        cost    = state_data.get("quality_cost")
        payload = state_data.get("quality_payload")
        provider_str = state_data.get("provider", "nano_banana")
        provider_enum = AIProvider.GPT_IMAGE if provider_str == "gpt_image" else AIProvider.NANO_BANANA
        provider_label = "GPT Image 2" if provider_str == "gpt_image" else "Nano Banana"

        if cost is None:
            # Fallback (photo flow): show quality keyboard
            await state.update_data(prompt=translated, original_prompt=prompt)
            await state.set_state(NanoBananaStates.waiting_for_quality)
            await message.answer(
                i18n.t(lang, "quality.select"),
                reply_markup=get_quality_keyboard(provider_str, lang)
            )
            return

        # Quality already selected → create job immediately
        job = GenerationService(db).create_job_for_user(
            telegram_user_id=user.telegram_user_id,
            provider=provider_enum,
            prompt=translated,
            original_prompt=prompt,
            source_image_url=state_data.get("source_image_url"),
            job_payload=payload,
            credits=cost,
        )
        msg = await message.answer(
            f"⏳ <b>{provider_label}</b> — задача принята.\n\n"
            f"💰 Списано: {cost} кр.\n🔄 Готовим результат... (~1–2 мин)",
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
