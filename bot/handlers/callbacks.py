from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from bot.keyboards.start import welcome_inline_keyboard
from bot.keyboards.main_menu import main_menu_keyboard
from shared.utils.i18n import I18n

from bot.states.nanobanana_states import NanoBananaStates
from bot.states.veo_states import VeoStates
from bot.states.kling_states import KlingStates
from shared.enums.providers import AIProvider

router = Router()
i18n = I18n()

@router.callback_query(F.data == "start_menu")
async def process_start_menu_callback(callback: CallbackQuery) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        lang = user_service.get_user_language(callback.from_user.id)

        await callback.message.answer(
            i18n.t(lang, "start.welcome"),
            reply_markup=main_menu_keyboard(lang),
        )
        await callback.message.answer(
            "👇",
            reply_markup=welcome_inline_keyboard(lang),
        )
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.startswith("gen_again:"))
async def process_gen_again_callback(callback: CallbackQuery, state: FSMContext) -> None:
    provider = callback.data.split(":")[1]
    
    if provider == AIProvider.NANO_BANANA:
        await state.set_state(NanoBananaStates.waiting_for_prompt)
        await callback.message.answer("Отправьте prompt для генерации изображения Nano Banana.")
    elif provider == AIProvider.VEO:
        await state.set_state(VeoStates.waiting_for_prompt)
        await callback.message.answer("Отправьте prompt для генерации видео через Veo.")
    elif provider == AIProvider.KLING:
        await state.set_state(KlingStates.waiting_for_prompt)
        await callback.message.answer("Отправьте prompt для анимации через Kling Motion.")
    else:
        await callback.message.answer("Неизвестный провайдер.")
        
    await callback.answer()


@router.callback_query(F.data == "buy_credits")
async def process_buy_credits_callback(callback: CallbackQuery) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        lang = user_service.get_user_language(callback.from_user.id)
        
        # They want to buy plans. We should refer them to the miniapp /plans page
        from backend.core.config import settings
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
        
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=i18n.t(lang, "menu.buy"),
                        web_app=WebAppInfo(url=settings.miniapp_url + "/plans")
                    )
                ]
            ]
        )
        await callback.message.answer(
            i18n.t(lang, "orders.choose_plan"),
            reply_markup=markup
        )
        await callback.answer()
    finally:
        db.close()
