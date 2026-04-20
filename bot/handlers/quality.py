import logging
import asyncio
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.quality_menu import QUALITY_DATA
from bot.states.veo_states import VeoStates
from bot.states.kling_states import KlingStates
from bot.states.nanobanana_states import NanoBananaStates
from bot.services.db_session import get_db_session
from backend.services.generation_service import GenerationService
from backend.services.user_service import UserService
from shared.enums.providers import AIProvider
from bot.services.progress import track_generation_progress
from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)
router = Router()
i18n = I18n()

@router.callback_query(F.data.startswith("q:"))
async def handle_quality_selection(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    _, provider_short, quality_tier = callback.data.split(":")
    key = f"{provider_short}:{quality_tier}"
    
    data = QUALITY_DATA.get(key)
    if not data:
        await callback.answer("Ошибка: данные для качества не найдены", show_alert=True)
        return

    state_data = await state.get_data()
    prompt = state_data.get("prompt")
    provider_str = state_data.get("provider", "")
    lang = state_data.get("lang", "ru")
    cost = data["cost"]
    payload = data["payload"]

    # ── New flow: quality selected BEFORE prompt ──────────────────────────────
    if not prompt:
        # Save quality to state, then ask for prompt
        await state.update_data(quality_cost=cost, quality_payload=payload)

        state_map = {
            "nano_banana": NanoBananaStates.waiting_for_prompt,
            "veo":         VeoStates.waiting_for_prompt,
            "kling":       KlingStates.waiting_for_prompt,
        }
        next_state = state_map.get(provider_str, NanoBananaStates.waiting_for_prompt)
        await state.set_state(next_state)

        prompt_key_map = {
            "nano_banana": "gen.prompt.nano",
            "veo":         "gen.prompt.veo",
            "kling":       "gen.prompt.kling",
        }
        prompt_text = i18n.t(lang, prompt_key_map.get(provider_str, "gen.prompt.nano"))
        try:
            await callback.message.edit_text(prompt_text, parse_mode="HTML")
        except Exception:
            await callback.message.answer(prompt_text, parse_mode="HTML")
        await callback.answer()
        return
    # ── Legacy / photo flow: prompt already in state → create job ─────────────

    original_prompt = state_data.get("original_prompt")
    source_image_url = state_data.get("source_image_url")

    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            return
        lang = user.language_code or lang

        provider_map = {
            "nano": AIProvider.NANO_BANANA,
            "veo":  AIProvider.VEO,
            "kling": AIProvider.KLING,
        }
        provider = provider_map.get(provider_short)

        from backend.core.config import settings
        is_admin = user.telegram_user_id in settings.admin_ids_list
        if not is_admin:
            from backend.services.balance_service import BalanceService
            balance = BalanceService(db).get_balance_value(user.id)
            if balance < cost:
                await callback.answer(i18n.t(lang, "errors.insufficient_funds"), show_alert=True)
                return

        gs = GenerationService(db)
        job = gs.create_job_for_user(
            telegram_user_id=user.telegram_user_id,
            provider=provider,
            prompt=prompt,
            original_prompt=original_prompt,
            source_image_url=source_image_url,
            job_payload=payload,
            credits=cost,
        )

        mode_text = {
            AIProvider.NANO_BANANA: "Nano Banana",
            AIProvider.VEO:         "Veo 3",
            AIProvider.KLING:       "Kling Motion",
        }.get(provider, "AI")

        status_text = (
            "⚡ Задача принята.\n👑 Режим администратора — кредиты не списываются."
            if is_admin else
            f"⏳ <b>{mode_text}</b> — задача принята.\n\n"
            f"💰 Списано: {cost} кр.\n🔄 Готовим результат..."
        )
        await callback.message.edit_text(status_text, parse_mode="HTML")
        asyncio.create_task(
            track_generation_progress(bot, callback.message.chat.id, callback.message.message_id, job.id)
        )
        await callback.answer()
        await state.clear()

    except Exception as e:
        logger.error(f"Error creating quality job: {e}")
        from bot.keyboards.reply_menu import main_reply_keyboard
        await callback.message.answer(
            "❌ Произошла ошибка. Попробуй ещё раз.\nКредиты не списаны.",
            reply_markup=main_reply_keyboard(lang)
        )
    finally:
        db.close()
