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
    source_image_url = state_data.get("source_image_url")
    
    if not prompt:
        await callback.answer("Ошибка: промпт потерян. Попробуйте снова.", show_alert=True)
        await state.clear()
        return

    db = next(get_db_session())
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            return
        lang = user.language_code or "ru"
        
        provider_map = {
            "nano": AIProvider.NANO_BANANA,
            "veo": AIProvider.VEO,
            "kling": AIProvider.KLING,
        }
        provider = provider_map.get(provider_short)
        
        cost = data["cost"]
        payload = data["payload"]
        
        # Check balance again (proactive)
        from backend.services.balance_service import BalanceService
        balance = BalanceService(db).get_balance_value(user.id)
        if balance < cost:
            await callback.answer(i18n.t(lang, "errors.insufficient_funds"), show_alert=True)
            return

        # Create job
        gs = GenerationService(db)
        job = gs.create_job_for_user(
            telegram_user_id=user.telegram_user_id,
            provider=provider,
            prompt=prompt,
            source_image_url=source_image_url,
            job_payload=payload,
            credits=cost,
        )
        
        # Show progress
        mode_text = {
            AIProvider.NANO_BANANA: "Nano Banana",
            AIProvider.VEO: "Veo 3",
            AIProvider.KLING: "Kling Motion",
        }.get(provider)
        
        await callback.message.edit_text(
            f"⏳ <b>{mode_text}</b> — задача #{job.id} принята.\n\n"
            f"💰 Списано: {cost} кр.\n"
            f"🔄 Готовим результат...",
            parse_mode="HTML"
        )
        
        asyncio.create_task(
            track_generation_progress(bot, callback.message.chat.id, callback.message.message_id, job.id)
        )
        
        await callback.answer()
        await state.clear()
        
    except Exception as exc:
        logger.error(f"Error creating quality job: {exc}")
        await callback.answer(f"❌ Ошибка: {exc}", show_alert=True)
    finally:
        db.close()
