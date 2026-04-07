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
        user = user_service.get_or_create_user(
            telegram_user_id=callback.from_user.id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
        )
        lang = (user.language_code if user else None) or "ru"
        name = user.first_name or callback.from_user.username or ("do'st" if lang == "uz" else "друг")

        if lang == "uz":
            text = (
                f"Xush kelibsiz, <b>{name}</b> 👋\n\n"
                f"<b>HARF AI</b> — sun'iy intellekt bilan rasm va video yarating.\n"
                f"━━━━━━━━━━━━━━\n"
                f"Quyidagi menyudan foydalaning 👇"
            )
        else:
            text = (
                f"Добро пожаловать, <b>{name}</b> 👋\n\n"
                f"<b>HARF AI</b> — создавайте изображения и видео с помощью нейросетей.\n"
                f"━━━━━━━━━━━━━━\n"
                f"Используйте меню ниже 👇"
            )
        from bot.keyboards.reply_menu import main_reply_keyboard
        try:
            await callback.message.edit_text(text, reply_markup=None, parse_mode="HTML")
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=main_reply_keyboard(lang), parse_mode="HTML")
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "menu_create")
async def process_menu_create(callback: CallbackQuery) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        lang = (user.language_code if user else None) or "ru"
    finally:
        db.close()

    title = "🎨 <b>Turni tanlang:</b>" if lang == "uz" else "🎨 <b>Выбери тип генерации:</b>"
    await callback.message.edit_text(
        title,
        reply_markup=create_submenu_keyboard(lang),
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

    # Step 1: Show quality/mode selection FIRST (before prompt)
    from bot.keyboards.quality_menu import get_quality_keyboard
    state_map = {
        "nano_banana": NanoBananaStates.waiting_for_quality,
        "veo":         VeoStates.waiting_for_quality,
        "kling":       KlingStates.waiting_for_quality,
    }
    quality_state = state_map.get(provider)
    if not quality_state:
        await callback.answer("Провайдер недоступен." if lang != "uz" else "Provayder mavjud emas.")
        return

    await state.set_state(quality_state)
    select_text = i18n.t(lang, "quality.select")
    await callback.message.answer(select_text, reply_markup=get_quality_keyboard(provider, lang))
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
    db = get_db_session()
    try:
        _us = UserService(db)
        _u = _us.get_user_by_telegram_id(callback.from_user.id)
        _lang = (_u.language_code if _u else None) or "ru"
    finally:
        db.close()
    _launch_msg = f"✅ Ishga tushiryapman: <i>{prompt[:100]}</i>" if _lang == "uz" else f"✅ Запускаю: <i>{prompt[:100]}</i>"
    await callback.message.answer(_launch_msg, parse_mode="HTML")

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
        lang = (user.language_code if user else None) or "ru"
        if user:
            credits = balance_service.get_balance_value(user.id)
            uzs_balance = getattr(user, "referral_earnings", 0) or 0
            uzs_fmt = f"{uzs_balance:,}".replace(",", " ")
            if lang == "uz":
                text = (
                    f"💳 <b>Balansingiz</b>\n\n"
                    f"⚡ Kreditlar: <b>{credits} kr.</b>\n"
                    f"💵 So'm balansi: <b>{uzs_fmt} so'm</b>\n\n"
                    f"Generatsiya narxlari:\n"
                    f"🍌 Nano Banana — 5–20 kr.\n"
                    f"🎬 Veo 3 — 30–80 kr.\n"
                    f"🎥 Kling — 40–120 kr."
                )
                btn_credits = "💎 Kredit sotib olish"
                btn_uzs = "💵 So'm balansi to'ldirish"
            else:
                text = (
                    f"💳 <b>Ваш баланс</b>\n\n"
                    f"⚡ Кредиты: <b>{credits} кр.</b>\n"
                    f"💵 Денежный баланс: <b>{uzs_fmt} сум</b>\n\n"
                    f"Стоимость генераций:\n"
                    f"🍌 Nano Banana — 5–20 кр.\n"
                    f"🎬 Veo 3 — 30–80 кр.\n"
                    f"🎥 Kling — 40–120 кр."
                )
                btn_credits = "💎 Купить кредиты"
                btn_uzs = "💵 Пополнить баланс в сумах"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=btn_credits, callback_data="menu_plans")],
                [InlineKeyboardButton(text=btn_uzs, callback_data="uzs_topup_menu")],
            ])
            await callback.message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "menu_plans")
async def process_menu_plans(callback: CallbackQuery) -> None:
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from bot.services.payment_service import PACKAGES

    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        lang = (user.language_code if user else None) or "ru"
    finally:
        db.close()

    def _fmt(n: int) -> str:
        return f"{n:,}".replace(",", " ")

    rows = []
    for pkg_id, pkg in PACKAGES.items():
        label = f"{pkg['name']} — {_fmt(pkg['price_uzs'])} {'so\'m' if lang == 'uz' else 'сум'} ({pkg['credits']} {'kr.' if lang == 'uz' else 'кр.'})"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"buy_pkg:{pkg_id}")])
    rows.append([InlineKeyboardButton(text="← " + ("Orqaga" if lang == "uz" else "Назад"), callback_data="start_menu")])

    if lang == "uz":
        text = (
            "💎 <b>HARF AI tariflari</b>\n\n"
            "✅ Kreditlar muddatsiz — xohlaganingizda foydalaning\n"
            "✅ To'lov: Click, Payme, Humo, Visa\n"
            "✅ Analoglardan 9% arzon\n\n"
            "🍌 Rasm = 5–20 kr.\n"
            "🎬 Video Veo3 = 30–80 kr.\n"
            "🎥 Video Kling = 40–120 kr.\n\n"
            "<i>Paketni tanlang:</i>"
        )
    else:
        text = (
            "💎 <b>Тарифы HARF AI</b>\n\n"
            "✅ Кредиты бессрочные — используйте когда угодно\n"
            "✅ Оплата: Click, Payme, Humo, Visa\n"
            "✅ На 9% выгоднее аналогов\n\n"
            "🍌 Картинка = 5–20 кр.\n"
            "🎬 Видео Veo3 = 30–80 кр.\n"
            "🎥 Видео Kling = 40–120 кр.\n\n"
            "<i>Выберите пакет:</i>"
        )

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy_pkg:"))
async def process_buy_package(callback: CallbackQuery, bot: Bot) -> None:
    from bot.services.payment_service import ManualPaymentService
    package_id = callback.data.split(":")[1]

    db = get_db_session()
    try:
        _us = UserService(db)
        _u = _us.get_user_by_telegram_id(callback.from_user.id)
        _lang = (_u.language_code if _u else None) or "ru"
    finally:
        db.close()

    try:
        await ManualPaymentService.send_invoice(
            bot=bot,
            chat_id=callback.from_user.id,
            telegram_user_id=callback.from_user.id,
            package_id=package_id,
        )
        await callback.answer()
    except Exception as e:
        err = f"Xatolik: {e}" if _lang == "uz" else f"Ошибка: {e}"
        await callback.answer(err, show_alert=True)


@router.callback_query(F.data == "buy_credits")
async def process_buy_credits_callback(callback: CallbackQuery) -> None:
    # Redirect to plans menu
    fake_callback = callback.model_copy(update={"data": "menu_plans"})
    await process_menu_plans(fake_callback)


# ── UZS Balance Top-up ─────────────────────────────────────────────────────

UZS_TOPUP_AMOUNTS = [
    (50_000,    "50 000"),
    (100_000,   "100 000"),
    (200_000,   "200 000"),
    (500_000,   "500 000"),
    (1_000_000, "1 000 000"),
]


async def send_uzs_topup_menu(send_fn, lang: str) -> None:
    """Shared helper — send the UZS top-up amount picker. send_fn is message.answer."""
    rows = [
        [InlineKeyboardButton(
            text=f"💵 {label} {'so\'m' if lang == 'uz' else 'сум'}",
            callback_data=f"uzs_topup:{amount}",
        )]
        for amount, label in UZS_TOPUP_AMOUNTS
    ]
    rows.append([InlineKeyboardButton(
        text="← " + ("Orqaga" if lang == "uz" else "Назад"),
        callback_data="menu_balance",
    )])

    if lang == "uz":
        text = (
            "💵 <b>So'm balansini to'ldirish</b>\n\n"
            "Summani tanlang:\n\n"
            "✅ Referal komissiyalari va boshqa to'lovlar\n"
            "ushbu balansga tushadi."
        )
    else:
        text = (
            "💵 <b>Пополнение денежного баланса</b>\n\n"
            "Выберите сумму:\n\n"
            "✅ Реферальные комиссии и пополнения\n"
            "накапливаются на этом балансе."
        )

    await send_fn(text, parse_mode="HTML",
                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data == "uzs_topup_menu")
async def process_uzs_topup_menu(callback: CallbackQuery) -> None:
    db = get_db_session()
    try:
        user = UserService(db).get_user_by_telegram_id(callback.from_user.id)
        lang = (user.language_code if user else None) or "ru"
    finally:
        db.close()

    await send_uzs_topup_menu(callback.message.answer, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("uzs_topup:"))
async def process_uzs_topup_amount(callback: CallbackQuery, bot: Bot) -> None:
    from backend.core.config import settings as _s

    amount = int(callback.data.split(":")[1])
    amount_fmt = f"{amount:,}".replace(",", " ")
    tg_id = callback.from_user.id

    db = get_db_session()
    try:
        user = UserService(db).get_user_by_telegram_id(tg_id)
        lang = (user.language_code if user else None) or "ru"
    finally:
        db.close()

    card = _s.card_number or "—"
    owner = _s.card_owner or "—"
    visa_card = _s.visa_card_number or ""
    visa_owner = _s.visa_card_owner or ""

    cards_text = ""
    if card and card != "—":
        cards_text += f"\n💳 <b>Humo / Uzcard</b>\n<code>{card}</code>\nPol.: <b>{owner}</b>"
    if visa_card:
        cards_text += f"\n\n💳 <b>Visa</b>\n<code>{visa_card}</code>\nPol.: <b>{visa_owner}</b>"
    if not cards_text:
        cards_text = "\n⚠️ " + ("Rekvizitlar sozlanmagan." if lang == "uz" else "Реквизиты не настроены.")

    if lang == "uz":
        text = (
            f"💵 <b>So'm balansini to'ldirish</b>\n\n"
            f"💰 Summa: <b>{amount_fmt} so'm</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"Quyidagi kartaga o'tkazing:{cards_text}\n"
            f"━━━━━━━━━━━━━━\n"
            f"<i>O'tkazgandan so'ng tugmani bosing 👇</i>"
        )
        btn_paid = "✅ O'tkazdim — tasdiqlash"
        btn_cancel = "❌ Bekor qilish"
    else:
        text = (
            f"💵 <b>Пополнение денежного баланса</b>\n\n"
            f"💰 Сумма: <b>{amount_fmt} сум</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"Переведите на карту:{cards_text}\n"
            f"━━━━━━━━━━━━━━\n"
            f"<i>После перевода нажмите кнопку 👇</i>"
        )
        btn_paid = "✅ Перевёл — подтвердить"
        btn_cancel = "❌ Отмена"

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_paid, callback_data=f"uzs_paid:{tg_id}:{amount}")],
            [InlineKeyboardButton(text=btn_cancel, callback_data="uzs_topup_menu")],
        ]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("uzs_paid:"))
async def process_uzs_paid(callback: CallbackQuery, bot: Bot) -> None:
    from backend.core.config import settings as _s
    import json as _json

    parts = callback.data.split(":")
    tg_id = int(parts[1])
    amount = int(parts[2])
    amount_fmt = f"{amount:,}".replace(",", " ")

    db = get_db_session()
    try:
        user = UserService(db).get_user_by_telegram_id(tg_id)
        lang = (user.language_code if user else None) or "ru"
        full_name = user.first_name or "—" if user else "—"
        username = user.username if user else None
    finally:
        db.close()

    # Confirm to user
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if lang == "uz":
        await callback.message.answer(
            "⏳ <b>Ariza tekshiruvga yuborildi</b>\n\n"
            "Odatda 1 soat ichida tasdiqlaymiz.\n"
            "Tasdiqlangach, so'm balansingizga avtomatik tushadi.",
            parse_mode="HTML",
        )
    else:
        await callback.message.answer(
            "⏳ <b>Заявка отправлена на проверку</b>\n\n"
            "Обычно подтверждаем в течение 1 часа.\n"
            "После проверки сумма зачислится на ваш баланс автоматически.",
            parse_mode="HTML",
        )

    # Notify admins
    uname = f"@{username}" if username else "—"
    confirm_kb = _json.dumps({"inline_keyboard": [[
        {"text": "✅ Подтвердить", "callback_data": f"uzs_ok:{tg_id}:{amount}"},
        {"text": "❌ Отклонить",   "callback_data": f"uzs_no:{tg_id}"},
    ]]})

    notify_chat = (_s.payment_notify_chat_id or "").strip()
    recipients = [int(notify_chat)] if notify_chat else list(_s.admin_ids_list)

    for chat_id in recipients:
        try:
            await bot.send_message(
                chat_id,
                f"💵 <b>ПОПОЛНЕНИЕ БАЛАНСА (СУМ)</b>\n\n"
                f"👤 {full_name}\n"
                f"🔗 {uname}\n"
                f"🆔 <code>{tg_id}</code>\n\n"
                f"💰 Сумма: <b>{amount_fmt} сум</b>\n\n"
                f"Проверь карту и нажми кнопку:",
                parse_mode="HTML",
                reply_markup=_json.loads(confirm_kb) if isinstance(confirm_kb, str) else None,
            )
        except Exception:
            # Send with raw reply_markup string via Bot API
            import httpx as _httpx
            try:
                async with _httpx.AsyncClient(timeout=10) as _c:
                    await _c.post(
                        f"https://api.telegram.org/bot{_s.bot_token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": (
                                f"💵 <b>ПОПОЛНЕНИЕ БАЛАНСА (СУМ)</b>\n\n"
                                f"👤 {full_name}\n🔗 {uname}\n"
                                f"🆔 <code>{tg_id}</code>\n\n"
                                f"💰 Сумма: <b>{amount_fmt} сум</b>\n\nПроверь карту:"
                            ),
                            "parse_mode": "HTML",
                            "reply_markup": confirm_kb,
                        },
                    )
            except Exception:
                pass

    await callback.answer()


@router.callback_query(F.data.startswith("uzs_ok:"))
async def process_uzs_confirm(callback: CallbackQuery, bot: Bot) -> None:
    from backend.core.config import settings as _s
    if callback.from_user.id not in _s.admin_ids_list:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    tg_id = int(parts[1])
    amount = int(parts[2])
    amount_fmt = f"{amount:,}".replace(",", " ")

    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(tg_id)
        if not user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        user.referral_earnings = (user.referral_earnings or 0) + amount
        db.commit()
        new_total = user.referral_earnings
        lang = user.language_code or "ru"
    finally:
        db.close()

    admin_name = callback.from_user.username or callback.from_user.first_name or "Admin"
    try:
        await callback.message.edit_text(
            callback.message.text + f"\n\n✅ Подтверждено @{admin_name}"
        )
    except Exception:
        pass

    total_fmt = f"{new_total:,}".replace(",", " ")
    if lang == "uz":
        user_text = (
            f"✅ <b>To'ldirish tasdiqlandi!</b>\n\n"
            f"💵 +{amount_fmt} so'm balansingizga qo'shildi\n"
            f"📊 Jami so'm balansi: <b>{total_fmt} so'm</b>"
        )
    else:
        user_text = (
            f"✅ <b>Пополнение подтверждено!</b>\n\n"
            f"💵 +{amount_fmt} сум зачислено на ваш баланс\n"
            f"📊 Итого денежный баланс: <b>{total_fmt} сум</b>"
        )
    try:
        await bot.send_message(tg_id, user_text, parse_mode="HTML")
    except Exception:
        pass

    await callback.answer(f"✅ Зачислено {amount_fmt} сум!")


@router.callback_query(F.data.startswith("uzs_no:"))
async def process_uzs_reject(callback: CallbackQuery, bot: Bot) -> None:
    from backend.core.config import settings as _s
    if callback.from_user.id not in _s.admin_ids_list:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    tg_id = int(callback.data.split(":")[1])

    db = get_db_session()
    try:
        user = UserService(db).get_user_by_telegram_id(tg_id)
        lang = (user.language_code if user else None) or "ru"
    finally:
        db.close()

    admin_name = callback.from_user.username or callback.from_user.first_name or "Admin"
    try:
        await callback.message.edit_text(
            callback.message.text + f"\n\n❌ Отклонено @{admin_name}"
        )
    except Exception:
        pass

    if lang == "uz":
        user_text = (
            f"❌ <b>To'ldirish rad etildi</b>\n\n"
            f"Karta raqami yoki summa to'g'ri emas.\n"
            f"Muammo bo'lsa: @{_s.support_username}"
        )
    else:
        user_text = (
            f"❌ <b>Пополнение отклонено</b>\n\n"
            f"Перевод не найден или указана неверная сумма.\n"
            f"Обратитесь в поддержку: @{_s.support_username}"
        )
    try:
        await bot.send_message(tg_id, user_text, parse_mode="HTML")
    except Exception:
        pass

    await callback.answer("❌ Отклонено")
