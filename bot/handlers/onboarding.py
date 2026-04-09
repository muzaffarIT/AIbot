from __future__ import annotations

import asyncio
import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from backend.services.user_service import UserService
from bot.services.db_session import get_db_session
from bot.keyboards.reply_menu import main_reply_keyboard
from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)
router = Router()
i18n = I18n()


class OnboardingStates(StatesGroup):
    step_1 = State()
    step_2 = State()
    step_3 = State()
    step_4 = State()


async def start_onboarding(message: types.Message, state: FSMContext, lang: str, name: str = "") -> None:
    """
    Walk the new user through 3 welcome screens, then show a 'Continue' button.
    All messages use parse_mode=HTML so bold/italic text renders correctly.
    """
    display_name = name or message.from_user.first_name or message.from_user.username or ("do'st" if lang == "uz" else "друг")

    await state.set_state(OnboardingStates.step_1)
    # Step 1 — greeting + credits awarded
    await message.answer(
        i18n.t(lang, "onboarding_step_1", name=display_name),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

    await asyncio.sleep(1.5)
    await state.set_state(OnboardingStates.step_2)
    # Step 2 — what AI models are available
    await message.answer(
        i18n.t(lang, "onboarding_step_2"),
        parse_mode="HTML",
    )

    await asyncio.sleep(1.5)
    await state.set_state(OnboardingStates.step_3)
    # Step 3 — call to action with Continue button
    await message.answer(
        i18n.t(lang, "onboarding_step_3"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(lang, "btn_continue"), callback_data="onboarding_next")]
        ]),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "onboarding_next", OnboardingStates.step_3)
async def onboarding_step_4(callback: types.CallbackQuery, state: FSMContext) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        lang = (user.language_code if user else None) or "ru"

        await state.set_state(OnboardingStates.step_4)
        await callback.message.edit_text(
            i18n.t(lang, "onboarding_step_4"),
            parse_mode="HTML",
        )

        if user:
            user.onboarding_completed = True
            db.commit()

        await state.clear()
        await callback.message.answer(
            i18n.t(lang, "onboarding_finished"),
            reply_markup=main_reply_keyboard(lang),
            parse_mode="HTML",
        )
        await callback.answer()
    finally:
        db.close()
