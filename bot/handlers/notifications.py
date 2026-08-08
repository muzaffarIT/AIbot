"""
Per-user notification opt-out.

Users can mute marketing broadcasts (daily bonus reminders, daily tips,
lifecycle nudges, win-back) without losing operational messages like
payment confirmations. This matters for deliverability: users who can't
silence us report/block the bot, and a rising block rate is what gets a
bot flagged by Telegram's anti-spam heuristics.
"""
import logging
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from shared.utils.i18n import I18n

router = Router()
i18n = I18n()
logger = logging.getLogger(__name__)


def _notifications_keyboard(enabled: bool, lang: str) -> InlineKeyboardMarkup:
    if enabled:
        btn_text = "🔕 Выключить" if lang != "uz" else "🔕 O'chirish"
        action = "notif_off"
    else:
        btn_text = "🔔 Включить" if lang != "uz" else "🔔 Yoqish"
        action = "notif_on"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_text, callback_data=action)],
        [InlineKeyboardButton(
            text="← Назад" if lang != "uz" else "← Orqaga",
            callback_data="start_menu",
        )],
    ])


@router.callback_query(F.data == "menu_notifications")
async def show_notifications(callback: CallbackQuery) -> None:
    db = get_db_session()
    try:
        user = UserService(db).get_user_by_telegram_id(callback.from_user.id)
        lang = (user.language_code if user else None) or "ru"
        enabled = bool(user and user.notifications_enabled)

        state = "✅ Включены" if enabled else "❌ Выключены"
        if lang == "uz":
            state = "✅ Yoqilgan" if enabled else "❌ O'chirilgan"
            text = (
                f"🔔 <b>Bildirishnomalar</b>\n\n"
                f"Hozir: <b>{state}</b>\n\n"
                f"Har kuni yuboraman:\n"
                f"• ☀️ ertalab — kunlik bonus eslatmasi\n"
                f"• 🌙 kechqurun — promptlar bo'yicha maslahatlar\n\n"
                f"Operatsion xabarlar (to'lovlar) baribir keladi."
            )
        else:
            text = (
                f"🔔 <b>Уведомления</b>\n\n"
                f"Сейчас: <b>{state}</b>\n\n"
                f"Каждый день я присылаю:\n"
                f"• ☀️ утром — напоминание забрать бонус\n"
                f"• 🌙 вечером — советы по промптам и идеи\n\n"
                f"Операционные сообщения (оплата) приходят в любом случае."
            )
        await callback.message.edit_text(
            text,
            reply_markup=_notifications_keyboard(enabled, lang),
            parse_mode="HTML",
        )
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.in_({"notif_on", "notif_off"}))
async def toggle_notifications(callback: CallbackQuery) -> None:
    db = get_db_session()
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer()
            return
        lang = user.language_code or "ru"

        enable = callback.data == "notif_on"
        # Only write when it actually changes to avoid useless UPDATEs.
        if user.notifications_enabled != enable:
            user.notifications_enabled = enable
            db.commit()

        alert = (
            "✅ Уведомления включены" if enable else "🔕 Уведомления выключены"
        ) if lang != "uz" else (
            "✅ Bildirishnomalar yoqildi" if enable else "🔕 Bildirishnomalar o'chirildi"
        )
        await callback.answer(alert, show_alert=True)

        # Re-render the panel with the new state.
        await show_notifications(callback)
    finally:
        db.close()
