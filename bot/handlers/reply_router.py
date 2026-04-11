"""
Reply keyboard message router.
Converts reply keyboard button text into handler actions.
"""
import asyncio
import logging
from aiogram import F, Router, Bot
from aiogram.types import Message, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.keyboards.reply_menu import REPLY_BUTTON_ACTIONS
from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from bot.keyboards.reply_menu import main_reply_keyboard
from bot.keyboards.main_menu import create_submenu_keyboard
from backend.core.config import settings
from bot.services.payment_service import ManualPaymentService, PACKAGES
from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)
router = Router()
i18n = I18n()

# Register all reply button texts
ALL_BUTTONS = list(REPLY_BUTTON_ACTIONS.keys())


@router.message(F.text.in_(ALL_BUTTONS))
async def handle_reply_button(message: Message, bot: Bot, state: FSMContext) -> None:
    await state.clear()
    action = REPLY_BUTTON_ACTIONS.get(message.text, "")

    db = get_db_session()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)
        user = user_service.get_or_create_user(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        lang = user.language_code or "ru"
        credits = balance_service.get_balance_value(user.id)

        if action == "menu_create":
            await message.answer(
                "🎨 <b>" + ("Yaratish turini tanlang:" if lang == "uz" else "Выбери тип генерации:") + "</b>",
                reply_markup=create_submenu_keyboard(lang),
                parse_mode="HTML",
            )

        elif action == "menu_plans":
            await _send_plans(message, bot, user, lang)

        elif action == "history_cmd":
            # Delegate to jobs handler via importing
            from bot.handlers.history import send_history as _send_history
            await _send_history(message)

        elif action == "menu_balance":
            uzs_balance = getattr(user, "uzs_balance", 0) or 0
            uzs_fmt = f"{uzs_balance:,}".replace(",", " ")

            # Get miniapp wallet URL — plain string, no keyboard objects
            wallet_url = ""
            try:
                raw = str(settings.miniapp_url or "").strip().rstrip("/")
                if raw and not raw.startswith("http"):
                    raw = "https://" + raw
                if raw:
                    wallet_url = raw + "/wallet"
            except Exception:
                pass

            if lang == "uz":
                text = (
                    f"💳 Balansingiz:\n\n"
                    f"⚡ Kreditlar: {credits} kr.\n"
                    f"💵 So'm balansi: {uzs_fmt} so'm"
                )
                if wallet_url:
                    text += f"\n\n💼 Kabinet: {wallet_url}"
            else:
                text = (
                    f"💳 Ваш баланс:\n\n"
                    f"⚡ Кредиты: {credits} кр.\n"
                    f"💵 Денежный баланс: {uzs_fmt} сум"
                )
                if wallet_url:
                    text += f"\n\n💼 Открыть кабинет: {wallet_url}"

            await message.answer(text)

        elif action == "menu_referral":
            from bot.handlers.referral import _send_referral_info
            await _send_referral_info(message.from_user.id, message, bot)

        elif action == "menu_language":
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            await message.answer(
                "🌍 Выберите язык / Tilni tanlang:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
                    InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="set_lang:uz"),
                ]])
            )

        elif action == "menu_help":
            from bot.handlers.help import show_help_cmd
            await show_help_cmd(message)

        elif action == "daily_bonus":
            from bot.handlers.daily import _handle_daily_bonus
            await _handle_daily_bonus(message.from_user.id, message, bot)

    finally:
        db.close()


async def _send_plans(message: Message, bot: Bot, user, lang: str) -> None:
    """Send plans/pricing information."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    def _fmt(n: int) -> str:
        return f"{n:,}".replace(",", " ")

    lines = ["💎 <b>" + ("Kreditlar paketi:" if lang == "uz" else "Кредитные пакеты:") + "</b>\n"]
    buttons = []
    for pkg_id, pkg in PACKAGES.items():
        name = pkg["name"]
        price = _fmt(pkg["price_uzs"])
        credits = pkg["credits"]
        lines.append(f"• {name} — {credits} кр. / {price} сум")
        buttons.append([InlineKeyboardButton(
            text=f"{name} — {price} сум",
            callback_data=f"buy_pkg:{pkg_id}"
        )])

    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="start_menu")])

    await message.answer(
        "\n".join(lines) + "\n\n<i>Оплата по карте — реквизиты придут после выбора.</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
