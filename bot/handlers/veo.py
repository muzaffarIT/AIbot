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

def _photo_action_keyboard(n_photos: int = 1) -> InlineKeyboardMarkup:
    """Build action keyboard. Shows photo counter + reset option when >1."""
    rows = [
        [InlineKeyboardButton(text="🍌 Image-to-Image Nano Banana", callback_data="photo:nano_banana")],
        [InlineKeyboardButton(text="🎨 Image-to-Image GPT Image 2", callback_data="photo:gpt_image")],
        [InlineKeyboardButton(text="🎬 Оживить через Veo 3", callback_data="photo:veo3")],
        [InlineKeyboardButton(text="🎥 Оживить через Kling", callback_data="photo:kling")],
    ]
    if n_photos > 1:
        rows.append([InlineKeyboardButton(text=f"🗑 Сбросить ({n_photos} фото)", callback_data="photo:reset")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="start_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# Backwards-compat alias used by tests / other modules
PHOTO_ACTION_KEYBOARD = _photo_action_keyboard(1)


@router.message(F.photo)
async def handle_photo_input(message: Message, state: FSMContext, bot: Bot) -> None:
    """Receives any photo and accumulates them for image-to-image / video tasks.

    Multiple photos can be added in two ways:
      • Telegram album (media_group_id) — all photos arrive as separate messages
        but share a media_group_id. We append each, but only show the action
        keyboard ONCE per album to avoid spam.
      • Sent one-by-one — each photo is appended; we re-show the keyboard so
        the user has a fresh button to tap. Whichever button they tap, the
        full accumulated list is used.
    """
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_url = f"https://api.telegram.org/file/bot{settings.bot_token}/{file.file_path}"

    state_data = await state.get_data()
    urls: list[str] = list(state_data.get("source_image_urls") or [])
    urls.append(file_url)

    caption = message.caption or ""
    # Caption logic: if user sent photo with caption, save caption as prompt
    # (only the first non-empty caption is taken — albums sometimes attach
    # caption only to the first item anyway)
    if caption.strip() and not state_data.get("prompt"):
        from bot.services.translator import translate_prompt
        translated = translate_prompt(caption.strip())
        await state.update_data(prompt=translated, original_prompt=caption.strip())

    await state.update_data(
        source_image_urls=urls,
        source_image_url=urls[0],  # back-compat for single-image consumers
    )

    # If a provider is already chosen and we're past selection, just acknowledge
    # silently (user is in waiting_for_prompt / waiting_for_quality state — they
    # changed their mind and added another photo). The accumulated list will be
    # used when the prompt / quality is finalised.
    current_state = await state.get_state()
    if current_state and "waiting_for" in current_state:
        await message.answer(f"📸 Добавлено. Всего фото: {len(urls)}")
        return

    # Album handling: only the FIRST photo of a media group shows the keyboard.
    media_group_id = message.media_group_id
    last_group = state_data.get("_last_media_group_id")
    if media_group_id and media_group_id == last_group:
        # already greeted this album — just silently absorb
        return
    if media_group_id:
        await state.update_data(_last_media_group_id=media_group_id)

    n = len(urls)
    counter_line = f"📸 Фото получено. Всего: <b>{n}</b>\n\n" if n > 1 else "📸 Фото получено!\n\n"
    hint = (
        "💡 Можно отправить ещё фото — все они уйдут в одну задачу.\n"
        "   (для Image-to-Image Nano / GPT — мульти-референс)\n\n"
    )
    body = (
        "✏️ После выбора — я создам задачу с твоим описанием."
        if caption.strip()
        else "✏️ После выбора — напиши промпт что должно происходить\n"
             "<i>Пример: she smiles slowly, cinematic</i>"
    )

    await message.answer(
        counter_line + hint + body,
        reply_markup=_photo_action_keyboard(n),
        parse_mode="HTML",
    )
    return


@router.callback_query(F.data == "photo:reset")
async def handle_photo_reset(callback, state: FSMContext) -> None:
    """Drop all collected photos and let the user start fresh."""
    await state.update_data(
        source_image_urls=[],
        source_image_url=None,
        _last_media_group_id=None,
    )
    await callback.message.answer("🗑 Список фото очищен. Отправь новое фото, чтобы начать заново.")
    await callback.answer("Фото сброшены")


@router.callback_query(F.data.startswith("photo:"))
async def handle_photo_action(callback, state: FSMContext) -> None:
    action = callback.data.split(":")[1]
    state_map = {
        "veo3": (VeoStates.waiting_for_prompt, "🎬 Veo 3 выбран. Напиши промпт для анимации этого фото:"),
        "kling": (KlingStates.waiting_for_prompt, "🎥 Kling Motion выбран. Напиши промпт для анимации:"),
        "nano_banana": (NanoBananaStates.waiting_for_prompt, "🍌 Nano Banana выбран. Напиши промпт для Image-to-Image:"),
        # GPT Image 2 reuses NanoBananaStates — image handler routes by state_data["provider"]
        "gpt_image": (NanoBananaStates.waiting_for_prompt, "🎨 GPT Image 2 выбран. Напиши промпт для Image-to-Image:"),
    }
    if action not in state_map:
        await callback.answer("Неизвестное действие.")
        return

    state_cls, text = state_map[action]
    # Record provider for downstream handlers (nanobanana handler reads this)
    await state.update_data(provider=action)
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

        # GPT Image 2 has a single tier — skip quality menu, create job directly.
        if provider == "gpt_image":
            from bot.keyboards.quality_menu import QUALITY_DATA as _QD
            tier = _QD["gpt:std"]
            await state.update_data(quality_cost=tier["cost"], quality_payload=tier["payload"])
            await state.set_state(NanoBananaStates.waiting_for_prompt)
            # Re-trigger the prompt handler by sending the saved prompt back through the bot
            from bot.handlers.nanobanana import handle_nanobanana_prompt
            state_data = await state.get_data()
            saved_prompt = state_data.get("prompt") or ""
            if saved_prompt:
                class _Fake:
                    text = saved_prompt
                    chat = message.chat
                    from_user = message.from_user
                    bot = message.bot
                    async def answer(self, *a, **kw): return await message.answer(*a, **kw)
                await handle_nanobanana_prompt(_Fake(), state)
            return

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
        img_urls: list[str] = list(state_data.get("source_image_urls") or [])
        img_url = source_image_url or (img_urls[0] if img_urls else state_data.get("source_image_url"))

        user = UserService(db).get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        # Veo 3 REFERENCE_2_VIDEO accepts a single reference image — use the first one.
        # Pass the full list along too in case provider integration evolves.
        job_payload = dict(payload_override or state_data.get("payload_overrides") or {})
        if img_urls:
            job_payload["source_image_urls"] = img_urls
        job = GenerationService(db).create_job_for_user(
            telegram_user_id=user.telegram_user_id,
            provider=AIProvider.VEO,
            prompt=prompt,
            source_image_url=img_url,
            job_payload=job_payload or None,
            credits=credits_override or state_data.get("cost"),
        )
        msg = await message.answer(
            "⏳ <b>Veo 3</b> — задача принята.\n\n"
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
        img_urls: list[str] = list(state_data.get("source_image_urls") or [])
        img_url = source_image_url or (img_urls[0] if img_urls else state_data.get("source_image_url"))

        user = UserService(db).get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        # Kling Motion takes a single source image. Pass list along for completeness.
        job_payload = dict(state_data.get("payload_overrides") or {})
        if img_urls:
            job_payload["source_image_urls"] = img_urls
        job = GenerationService(db).create_job_for_user(
            telegram_user_id=user.telegram_user_id,
            provider=AIProvider.KLING,
            prompt=prompt,
            source_image_url=img_url,
            job_payload=job_payload or None,
            credits=state_data.get("cost"),
        )
        msg = await message.answer(
            "⏳ <b>Kling Motion</b> — задача принята.\n\n"
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


