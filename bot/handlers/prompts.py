import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.data.prompts import PROMPTS, CATEGORY_LABELS_RU, CATEGORY_LABELS_UZ, get_random_prompt
from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)
router = Router()
i18n = I18n()

class PromptStates(StatesGroup):
    choosing_category = State()
    viewing_prompt = State()

def get_categories_keyboard(lang: str) -> InlineKeyboardMarkup:
    labels = CATEGORY_LABELS_UZ if lang == "uz" else CATEGORY_LABELS_RU
    buttons = []
    # Create grid 2xN
    row = []
    for cat_id, label in labels.items():
        row.append(InlineKeyboardButton(text=label, callback_query_data=f"prompt_cat:{cat_id}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(F.text.in_(["✨ Удиви меня", "✨ Meni hayrat qoldiring"]))
async def surprise_me_msg(message: Message, state: FSMContext) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(message.from_user.id)
        if not user:
            return
        lang = user.language_code or "ru"
        
        await state.set_state(PromptStates.choosing_category)
        await message.answer(
            i18n.t(lang, "prompts.category.select"),
            reply_markup=get_categories_keyboard(lang)
        )
    finally:
        db.close()

@router.callback_query(F.data.startswith("prompt_cat:"))
async def select_category(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id = callback.data.split(":")[1]
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            return
        lang = user.language_code or "ru"

        _, prompt = get_random_prompt(cat_id)
        
        await state.update_data(current_prompt=prompt, current_category=cat_id)
        await state.set_state(PromptStates.viewing_prompt)
        
        text = i18n.t(lang, "prompts.selected", prompt=prompt)
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t(lang, "prompts.btn.use"), callback_query_data="prompt_use"),
                InlineKeyboardButton(text=i18n.t(lang, "prompts.btn.another"), callback_query_data=f"prompt_cat:{cat_id}")
            ],
            [
                InlineKeyboardButton(text=i18n.t(lang, "prompts.btn.own"), callback_query_data="prompt_own")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
    finally:
        db.close()

@router.callback_query(F.data == "prompt_use")
async def use_prompt(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    prompt = data.get("current_prompt")
    cat = data.get("current_category")
    
    if not prompt:
        await callback.answer("Ошибка: промпт не найден", show_alert=True)
        return

    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        lang = user.language_code or "ru"

        await state.update_data(prompt=prompt)
        
        if cat == "video":
            from bot.handlers.veo import VeoStates, show_veo_quality_selection
            await state.set_state(VeoStates.waiting_for_quality)
            await show_veo_quality_selection(callback.message, lang)
        else:
            from bot.handlers.nanobanana import NanoBananaStates, show_banana_quality_selection
            await state.set_state(NanoBananaStates.waiting_for_quality)
            await show_banana_quality_selection(callback.message, lang)

        await callback.answer()
    finally:
        db.close()

@router.callback_query(F.data == "prompt_own")
async def own_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    # Just clear state and ask to use normal creation buttons
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        lang = user.language_code or "ru"
        
        await state.clear()
        await callback.message.edit_text(i18n.t(lang, "help.text")) # Or just a hint
        await callback.answer()
    finally:
        db.close()
