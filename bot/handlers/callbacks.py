import asyncio
from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from bot.keyboards.main_menu import main_inline_keyboard, create_submenu_keyboard
from shared.utils.i18n import I18n

from bot.states.nanobanana_states import NanoBananaStates
from bot.states.veo_states import VeoStates
from bot.states.kling_states import KlingStates
from shared.enums.providers import AIProvider

router = Router()
i18n = I18n()


@router.callback_query(F.data == "start_menu")
async def process_start_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)
        user = user_service.get_or_create_user(
            telegram_user_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
        )
        credits = balance_service.get_balance_value(user.id)
        name = user.first_name or callback.from_user.username or "друг"

        text = (
            f"👋 Привет, <b>{name}</b>!\n"
            f"Добро пожаловать в <b>BATIR AI</b>.\n"
            f"У тебя <b>{credits}</b> кредитов.\n\n"
            f"Выбери действие:"
        )
        await callback.message.edit_text(text, reply_markup=main_inline_keyboard(), parse_mode="HTML")
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "menu_create")
async def process_menu_create(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🎨 <b>Выбери тип генерации:</b>",
        reply_markup=create_submenu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("gen_start:"))
async def process_gen_start(callback: CallbackQuery, state: FSMContext) -> None:
    provider = callback.data.split(":")[1]

    prompts = {
        AIProvider.NANO_BANANA: (
            NanoBananaStates.waiting_for_prompt,
            "🍌 <b>Nano Banana</b> — генерация изображения\n\n"
            "✏️ Напиши промпт на английском:\n<i>Пример: a futuristic cat in neon city, 4k, cinematic</i>\n\n"
            "📎 Или отправь фото + промпт в подписи для Image-to-Image",
        ),
        AIProvider.VEO: (
            VeoStates.waiting_for_prompt,
            "🎬 <b>Veo 3</b> — генерация видео\n\n"
            "✏️ Напиши промпт:\n<i>Пример: a dragon flying over mountains, epic, slow motion</i>\n\n"
            "📎 Или отправь фото + промпт чтобы оживить изображение",
        ),
        AIProvider.KLING: (
            KlingStates.waiting_for_prompt,
            "🎥 <b>Kling Motion</b> — анимация\n\n"
            "✏️ Напиши промпт:\n<i>Пример: she smiles slowly, cinematic, portrait</i>\n\n"
            "📎 Или отправь фото + промпт чтобы оживить изображение",
        ),
    }

    if provider not in prompts:
        await callback.answer("Неизвестный провайдер.")
        return

    state_cls, text = prompts[provider]
    await state.set_state(state_cls)
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("gen_again:"))
async def process_gen_again_callback(callback: CallbackQuery, state: FSMContext) -> None:
    provider = callback.data.split(":")[1]
    # Re-use gen_start logic
    fake_data = f"gen_start:{provider}"
    fake_callback = callback.model_copy(update={"data": fake_data})
    await process_gen_start(fake_callback, state)


@router.callback_query(F.data == "menu_balance")
async def process_menu_balance(callback: CallbackQuery) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if user:
            credits = balance_service.get_balance_value(user.id)
            await callback.message.answer(
                f"💰 <b>Ваш баланс:</b> <b>{credits}</b> кредитов\n\n"
                f"Стоимость генераций:\n"
                f"🍌 Nano Banana — 5 кр.\n"
                f"🎬 Veo 3 (fast) — 30 кр.\n"
                f"🎥 Kling Motion (std) — 40 кр.",
                parse_mode="HTML",
                reply_markup=main_inline_keyboard(),
            )
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "menu_plans")
async def process_menu_plans(callback: CallbackQuery) -> None:
    from backend.core.config import settings
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    from bot.services.payment_service import PACKAGES, BotPaymentService

    rows = []
    for pkg_id, pkg in PACKAGES.items():
        rows.append([
            InlineKeyboardButton(
                text=f"{pkg['name']} — {pkg['price_usd']} ({pkg['credits']} кр.)",
                callback_data=f"buy_pkg:{pkg_id}"
            )
        ])
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="start_menu")])

    await callback.message.answer(
        "💎 <b>Выберите пакет кредитов:</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_pkg:"))
async def process_buy_package(callback: CallbackQuery, bot: Bot) -> None:
    from bot.services.payment_service import BotPaymentService
    package_id = callback.data.split(":")[1]
    try:
        await BotPaymentService.send_invoice(bot, callback.from_user.id, package_id)
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "buy_credits")
async def process_buy_credits_callback(callback: CallbackQuery) -> None:
    # Redirect to plans menu
    fake_callback = callback.model_copy(update={"data": "menu_plans"})
    await process_menu_plans(fake_callback)
