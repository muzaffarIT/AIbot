import asyncio
import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from bot.services.db_session import get_db_session
from bot.keyboards.reply_menu import main_reply_keyboard
from bot.keyboards.main_menu import main_inline_keyboard
from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)
router = Router()
i18n = I18n()

class OnboardingStates(StatesGroup):
    step_1 = State()
    step_2 = State()
    step_3 = State()
    step_4 = State()

async def start_onboarding(message: types.Message, state: FSMContext, lang: str, name: str = ""):
    await state.set_state(OnboardingStates.step_1)
    step1_text = i18n.t(lang, "onboarding_step_1")
    if name and "{name}" in step1_text:
        step1_text = step1_text.replace("{name}", name)
    await message.answer(
        step1_text,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await asyncio.sleep(1.5)
    await state.set_state(OnboardingStates.step_2)
    await message.answer(i18n.t(lang, "onboarding_step_2"), parse_mode="HTML")

    await asyncio.sleep(1.5)
    await state.set_state(OnboardingStates.step_3)
    await message.answer(
        i18n.t(lang, "onboarding_step_3"),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=i18n.t(lang, "btn_continue"), callback_data="onboarding_next")]
        ])
    )

@router.callback_query(F.data == "onboarding_next", OnboardingStates.step_3)
async def onboarding_step_4(callback: types.CallbackQuery, state: FSMContext):
    db = get_db_session()
    try:
        user_service = UserService(db)
        # Always use DB language (set by user in bot), not Telegram's app language
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        lang = (user.language_code if user else None) or "ru"

        await state.set_state(OnboardingStates.step_4)
        await callback.message.edit_text(i18n.t(lang, "onboarding_step_4"), parse_mode="HTML")

        # Finalize onboarding
        if user:
            user.onboarding_completed = True
            db.commit()

        await state.clear()
        await callback.message.answer(
            i18n.t(lang, "onboarding_finished"),
            reply_markup=main_reply_keyboard(lang)
        )
        await callback.answer()

        # ── Show a "wow" example right after onboarding ──────────────────
        # The single biggest new-user drop-off in AI bots is "I don't know
        # what to write". Showing a finished example with a ready-to-use
        # prompt (Suzma's Reels trick, in-bot) collapses that barrier and
        # pushes the user to their first generation immediately.
        try:
            from bot.handlers.showcase import send_showcase
            from bot.keyboards.main_menu import main_inline_keyboard
            # Lead with the menu so they have navigation, then the showcase
            # example on top as the call-to-action.
            await callback.message.answer(
                i18n.t(lang, "showcase.intro") if lang != "uz"
                else i18n.t(lang, "showcase.intro"),
                reply_markup=main_inline_keyboard(lang),
                parse_mode="HTML",
            )
            await send_showcase(callback.message, callback.from_user.id)
        except Exception as e:
            logger.warning(f"[Onboarding] showcase step failed (non-fatal): {e}")
    finally:
        db.close()
