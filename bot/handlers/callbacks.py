import asyncio
from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from bot.keyboards.main_menu import create_submenu_keyboard
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
            f"Добро пожаловать в <b>HARF AI</b>.\n"
            f"У тебя <b>{credits}</b> кредитов.\n\n"
            f"Выбери действие:"
        )
        await callback.message.edit_text(text, reply_markup=None, parse_mode="HTML")
        await callback.message.answer("👇 Выберите действие в меню ниже:")
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
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        lang = (user.language_code if user else None) or "ru"
    finally:
        db.close()

    await state.update_data(provider=provider, lang=lang)

    if provider == "nano_banana":
        await state.set_state(NanoBananaStates.waiting_for_prompt)
        prompt_text = i18n.t(lang, "gen.prompt.nano")
    elif provider == "veo":
        await state.set_state(VeoStates.waiting_for_prompt)
        prompt_text = i18n.t(lang, "gen.prompt.veo")
    elif provider == "kling":
        await state.set_state(KlingStates.waiting_for_prompt)
        prompt_text = i18n.t(lang, "gen.prompt.kling")
    else:
        await callback.answer("Неизвестный провайдер.")
        return

    await callback.message.answer(prompt_text, parse_mode="HTML")
    await callback.answer()



@router.callback_query(F.data == "surprise_me")
async def process_surprise_me(callback: CallbackQuery, state: FSMContext) -> None:
    from bot.data.prompts import get_random_prompt, CATEGORY_LABELS_RU, CATEGORY_LABELS_UZ, VIDEO_CATEGORIES
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        lang = (user.language_code if user else None) or "ru"
    finally:
        db.close()

    cat, prompt = get_random_prompt()
    labels = CATEGORY_LABELS_UZ if lang == "uz" else CATEGORY_LABELS_RU
    tip = i18n.t(lang, "prompts.tip")

    # Set state based on whether it's video
    if cat in VIDEO_CATEGORIES:
        await state.update_data(provider="veo", quality="fast", cost=30,
                                payload_overrides={"quality": "fast", "duration": 8})
        await state.set_state(VeoStates.waiting_for_prompt)
    else:
        await state.update_data(provider="nano_banana", quality="hd", cost=10,
                                payload_overrides={"width": 1024, "height": 1024})
        await state.set_state(NanoBananaStates.waiting_for_prompt)

    text = i18n.t(lang, "prompts.selected", prompt=prompt)
    await callback.message.answer(
        text + f"\n\n{tip}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=i18n.t(lang, "prompts.btn.use"), callback_data=f"use_prompt:{prompt[:100]}"),
                InlineKeyboardButton(text=i18n.t(lang, "prompts.btn.another"), callback_data="surprise_me"),
            ],
            [InlineKeyboardButton(text=i18n.t(lang, "prompts.btn.own"), callback_data="cancel_prompt")],
        ]),
        parse_mode="HTML",
    )
    await state.update_data(suggested_prompt=prompt)
    await callback.answer()


@router.callback_query(F.data.startswith("use_prompt:"))
async def use_suggested_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    """User accepted the suggested prompt — run it directly."""
    from bot.handlers.nanobanana import create_nanobanana_job
    data = await state.get_data()
    prompt = data.get("suggested_prompt", callback.data.split(":", 1)[1])
    provider = data.get("provider", "nano_banana")

    # Artificial message with the prompt to reuse existing handlers
    await callback.message.answer(f"✅ Запускаю: <i>{prompt[:100]}</i>", parse_mode="HTML")

    class _FakeMessage:
        text = prompt
        chat = callback.message.chat
        from_user = callback.from_user
        bot = callback.bot
        async def answer(self, *a, **kw): return await callback.message.answer(*a, **kw)
        parse_mode = "HTML"

    fake = _FakeMessage()
    if provider == "veo":
        from bot.handlers.veo import _create_veo_job
        await _create_veo_job(fake, state, prompt)
    elif provider == "kling":
        from bot.handlers.veo import _create_kling_job
        await _create_kling_job(fake, state, prompt)
    else:
        from bot.handlers.nanobanana import create_nanobanana_job
        # Use the state FSM path:
        fake.text = prompt
        await create_nanobanana_job(fake, state)
    await callback.answer()


@router.callback_query(F.data == "cancel_prompt")
async def cancel_suggested_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        lang = (user.language_code if user else None) or "ru"
    finally:
        db.close()

    from bot.keyboards.main_menu import create_submenu_keyboard
    msg = "Хорошо! Выбери нейросеть:" if lang != "uz" else "Yaxshi! Neyrosetni tanlang:"
    await state.clear()
    await callback.message.answer(msg, reply_markup=create_submenu_keyboard(lang))
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
                reply_markup=None,
            )
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "menu_plans")
async def process_menu_plans(callback: CallbackQuery) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from bot.services.payment_service import PACKAGES

    def _fmt(n: int) -> str:
        return f"{n:,}".replace(",", " ")

    rows = []
    for pkg_id, pkg in PACKAGES.items():
        rows.append([
            InlineKeyboardButton(
                text=f"{pkg['name']} — {_fmt(pkg['price_uzs'])} сум ({pkg['credits']} кр.)",
                callback_data=f"buy_pkg:{pkg_id}"
            )
        ])
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="start_menu")])

    await callback.message.answer(
        "💎 <b>Выберите пакет кредитов:</b>\n\n"
        "Оплата по карте — реквизиты придут после выбора.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_pkg:"))
async def process_buy_package(callback: CallbackQuery, bot: Bot) -> None:
    from bot.services.payment_service import ManualPaymentService
    package_id = callback.data.split(":")[1]
    try:
        await ManualPaymentService.send_invoice(
            bot=bot,
            chat_id=callback.from_user.id,
            telegram_user_id=callback.from_user.id,
            package_id=package_id,
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)


@router.callback_query(F.data == "buy_credits")
async def process_buy_credits_callback(callback: CallbackQuery) -> None:
    # Redirect to plans menu
    fake_callback = callback.model_copy(update={"data": "menu_plans"})
    await process_menu_plans(fake_callback)
