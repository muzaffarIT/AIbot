import asyncio
from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from backend.services.generation_service import GenerationService
from backend.services.user_service import UserService
from bot.services.db_session import get_db_session
from bot.states.veo_states import VeoStates
from bot.states.kling_states import KlingStates
from shared.enums.providers import AIProvider
from shared.utils.i18n import I18n
from bot.services.progress import track_generation_progress
from backend.core.config import settings
from bot.keyboards.quality_menu import get_quality_keyboard
from bot.states.nanobanana_states import NanoBananaStates

router = Router()
i18n = I18n()

VEO_TRIGGERS = {
    i18n.t("ru", "menu.create_video"),
    i18n.t("uz", "menu.create_video"),
}

PHOTO_ACTION_KEYBOARD = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Оживить через Veo 3", callback_data="photo:veo3")],
        [InlineKeyboardButton(text="🎥 Оживить через Kling", callback_data="photo:kling")],
        [InlineKeyboardButton(text="🍌 Image-to-Image Nano Banana", callback_data="photo:nano_banana")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="start_menu")],
    ]
)


@router.message(F.photo)
async def handle_photo_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Works globally — receives any photo and asks what to do with it."""
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{settings.bot_token}/{file.file_path}"

    caption = message.caption or ""
    # Caption logic: if user sent photo with caption, save caption as prompt
    if caption.strip():
        from bot.services.translator import translate_prompt
        translated = translate_prompt(caption.strip())
        await state.update_data(prompt=translated, original_prompt=caption.strip())
    
    await state.update_data(source_image_url=file_url)
    
    # We always show the action keyboard because we don't know if they want Nano, Veo, or Kling
    await message.answer(
        "📸 Фото получено! Что сделать?\n\n"
        "✏️ После выбора — я создам задачу с твоим описанием." if caption.strip() else 
        "📸 Фото получено! Что сделать?\n\n"
        "✏️ После выбора — напиши промпт что должно происходить\n"
        "<i>Пример: she smiles slowly, cinematic</i>",
        reply_markup=PHOTO_ACTION_KEYBOARD,
        parse_mode="HTML",
    )
    return


@router.callback_query(F.data.startswith("photo:"))
async def handle_photo_action(callback, state: FSMContext) -> None:
    action = callback.data.split(":")[1]
    state_map = {
        "veo3": (VeoStates.waiting_for_prompt, "🎬 Veo 3 выбран. Напиши промпт для анимации этого фото:"),
        "kling": (KlingStates.waiting_for_prompt, "🎥 Kling Motion выбран. Напиши промпт для анимации:"),
        "nano_banana": (NanoBananaStates.waiting_for_prompt, "🍌 Nano Banana выбран. Напиши промпт для Image-to-Image:"),
    }
    state_cls, text = state_map[action]
    await state.set_state(state_cls)

    if action not in state_map:
        await callback.answer("Неизвестное действие.")
        return

    state_cls, text = state_map[action]
    await state.set_state(state_cls)
    
    state_data = await state.get_data()
    if state_data.get("prompt"):
        # We already have a prompt from caption! Go to quality selection.
        await _show_provider_quality(callback.message, state, action)
        await callback.answer()
        return

    await callback.message.answer(text)
    await callback.answer()


async def _show_provider_quality(message: Message, state: FSMContext, provider: str) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(message.chat.id)
        lang = user.language_code or "ru"
        
        # Map action keys to quality keyboard keys
        kb_key = "nano_banana" if provider == "nano_banana" else provider
        
        # Set specific quality waiting state
        if provider == "veo3": await state.set_state(VeoStates.waiting_for_quality)
        elif provider == "kling": await state.set_state(KlingStates.waiting_for_quality)
        elif provider == "nano_banana": 
            await state.set_state(NanoBananaStates.waiting_for_quality)

        await message.answer(
            i18n.t(lang, "quality.select"),
            reply_markup=get_quality_keyboard(kb_key, lang)
        )
    finally:
        db.close()


async def _create_veo_job(message: Message, state: FSMContext, prompt: str, source_image_url: str | None = None,
                          payload_override: dict | None = None, credits_override: int | None = None) -> None:
    db = get_db_session()
    try:
        state_data = await state.get_data()
        img_url = source_image_url or state_data.get("source_image_url")

        user = UserService(db).get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        job = GenerationService(db).create_job_for_user(
            telegram_user_id=user.telegram_user_id,
            provider=AIProvider.VEO,
            prompt=prompt,
            source_image_url=img_url,
            job_payload=payload_override or state_data.get("payload_overrides"),
            credits=credits_override or state_data.get("cost"),
        )
        msg = await message.answer(
            f"⏳ <b>Veo 3</b> — задача #{job.id} в очереди.\n\n"
            "🔄 Обычно видео готовится 2-5 минут.\nМы пришлём уведомление когда будет готово!",
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


async def _create_kling_job(message: Message, state: FSMContext, prompt: str, source_image_url: str | None = None) -> None:
    db = get_db_session()
    try:
        state_data = await state.get_data()
        img_url = source_image_url or state_data.get("source_image_url")

        user = UserService(db).get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        job = GenerationService(db).create_job_for_user(
            telegram_user_id=user.telegram_user_id,
            provider=AIProvider.KLING,
            prompt=prompt,
            source_image_url=img_url,
            job_payload=state_data.get("payload_overrides"),
            credits=state_data.get("cost"),
        )
        msg = await message.answer(
            f"⏳ <b>Kling Motion</b> — задача #{job.id} в очереди.\n\n"
            "🔄 Анимация обычно готовится 3-7 минут.",
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


@router.message(VeoStates.waiting_for_prompt, F.text)
async def handle_veo_prompt_msg(message: Message, state: FSMContext) -> None:
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

        if cost is None:
            # Fallback (photo flow): show quality keyboard
            await state.update_data(prompt=translated, original_prompt=prompt)
            await state.set_state(VeoStates.waiting_for_quality)
            from bot.keyboards.quality_menu import get_quality_keyboard
            await message.answer(
                i18n.t(lang, "quality.select"),
                reply_markup=get_quality_keyboard("veo", lang)
            )
            return

        # Quality already selected → create job immediately
        await _create_veo_job(message, state, translated, payload_override=payload, credits_override=cost)
    finally:
        db.close()


