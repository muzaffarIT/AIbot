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
    if caption.strip():
        # We have prompt in caption — check state and create job directly
        current_state = await state.get_state()
        if current_state in (VeoStates.waiting_for_prompt, str(VeoStates.waiting_for_prompt)):
            await _create_veo_job(message, state, caption.strip(), file_url)
            return
        if current_state in (KlingStates.waiting_for_prompt, str(KlingStates.waiting_for_prompt)):
            await _create_kling_job(message, state, caption.strip(), file_url)
            return

    # No active state, or no caption — save url and show action keyboard
    await state.update_data(source_image_url=file_url)
    await message.answer(
        "📸 Фото получено! Что сделать?\n\n"
        "✏️ После выбора — напиши промпт что должно происходить\n"
        "<i>Пример: she smiles slowly, cinematic</i>",
        reply_markup=PHOTO_ACTION_KEYBOARD,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("photo:"))
async def handle_photo_action(callback, state: FSMContext) -> None:
    action = callback.data.split(":")[1]
    state_map = {
        "veo3": (VeoStates.waiting_for_prompt, "🎬 Veo 3 выбран. Напиши промпт для анимации этого фото:"),
        "kling": (KlingStates.waiting_for_prompt, "🎥 Kling Motion выбран. Напиши промпт для анимации:"),
        "nano_banana": ("nano:waiting", "🍌 Nano Banana выбран. Напиши промпт для Image-to-Image:"),
    }
    from bot.states.nanobanana_states import NanoBananaStates
    state_map["nano_banana"] = (NanoBananaStates.waiting_for_prompt, "🍌 Nano Banana. Напиши промпт для Image-to-Image преобразования:")

    if action not in state_map:
        await callback.answer("Неизвестное действие.")
        return

    state_cls, text = state_map[action]
    await state.set_state(state_cls)
    await callback.message.answer(text)
    await callback.answer()


async def _create_veo_job(message: Message, state: FSMContext, prompt: str, source_image_url: str | None = None) -> None:
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
async def create_veo_job_from_text(message: Message, state: FSMContext) -> None:
    prompt = message.text or ""
    if len(prompt) < 3 or len(prompt) > 500:
        await message.answer("❌ Длина промпта: от 3 до 500 символов.")
        return
    await _create_veo_job(message, state, prompt)


@router.message(KlingStates.waiting_for_prompt, F.text)
async def create_kling_job_from_text(message: Message, state: FSMContext) -> None:
    prompt = message.text or ""
    if len(prompt) < 3 or len(prompt) > 500:
        await message.answer("❌ Длина промпта: от 3 до 500 символов.")
        return
    await _create_kling_job(message, state, prompt)
