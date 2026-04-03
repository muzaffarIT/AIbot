"""
Manual payment handlers for HARF AI bot.
Flow:
  1. User selects plan → send_invoice shows card + amount
  2. User clicks "✅ Я оплатил" → admins notified
  3. Admin clicks "✅ Подтвердить" → credits added, user notified
  4. Admin clicks "❌ Отклонить" → reject reason menu → user notified
"""

import json
import logging
from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from backend.core.config import settings
from bot.services.payment_service import ManualPaymentService, PACKAGES

logger = logging.getLogger(__name__)
router = Router()


# ── MiniApp web_app_data ────────────────────────────────────────────────────

@router.message(F.web_app_data)
async def web_app_data_handler(message: Message, bot: Bot) -> None:
    """Handle buy requests sent from the Telegram MiniApp."""
    data = message.web_app_data.data
    try:
        parsed = json.loads(data)
        if parsed.get("action") == "buy_plan":
            package_id = parsed.get("package_id")
            if package_id and package_id in PACKAGES:
                await ManualPaymentService.send_invoice(
                    bot=bot,
                    chat_id=message.chat.id,
                    telegram_user_id=message.from_user.id,
                    package_id=package_id,
                )
            else:
                await message.answer("⚠️ Неизвестный тариф. Попробуйте снова.")
    except Exception as e:
        logger.error(f"web_app_data_handler error: {e}")
        try:
            await message.answer(
                "⚠️ Произошла ошибка при создании заявки. Попробуйте ещё раз или обратитесь в поддержку."
            )
        except Exception:
            pass


def _is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids_list


# ── User: confirmed payment ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("manual_paid:"))
async def cb_manual_paid(callback: CallbackQuery, bot: Bot) -> None:
    payment_id = int(callback.data.split(":")[1])

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        "⏳ <b>Заявка отправлена на проверку</b>\n\n"
        "Обычно подтверждаем в течение 1 часа.\n"
        "Как только проверим перевод — кредиты зачислятся автоматически.",
        parse_mode="HTML",
    )

    # Determine package_id from payment record to include in admin message
    from bot.services.db_session import get_db_session
    from backend.db.repositories.payments import PaymentRepository
    from backend.db.repositories.orders import OrderRepository
    from backend.db.repositories.plans import PlanRepository

    package_id = "pro"  # fallback
    db = get_db_session()
    try:
        pay_repo = PaymentRepository(db)
        order_repo = OrderRepository(db)
        plan_repo = PlanRepository(db)
        payment = pay_repo.get_by_id(payment_id)
        if payment:
            order = order_repo.get_by_id(payment.order_id)
            if order:
                plan = plan_repo.get_by_id(order.plan_id)
                if plan:
                    # find matching package by plan_code
                    for pkg_id, pkg in PACKAGES.items():
                        if pkg["plan_code"] == plan.code:
                            package_id = pkg_id
                            break
    finally:
        db.close()

    user = callback.from_user
    full_name = user.full_name or user.first_name or "—"
    await ManualPaymentService.notify_admins_payment_submitted(
        bot=bot,
        payment_id=payment_id,
        telegram_user_id=user.id,
        user_full_name=full_name,
        username=user.username,
        package_id=package_id,
    )
    await callback.answer()


# ── User: cancel payment ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("manual_cancel:"))
async def cb_manual_cancel(callback: CallbackQuery) -> None:
    payment_id = int(callback.data.split(":")[1])

    from bot.services.db_session import get_db_session
    from backend.db.repositories.payments import PaymentRepository
    from backend.db.repositories.orders import OrderRepository
    from shared.enums.payment_status import PaymentStatus
    from shared.enums.order_status import OrderStatus

    db = get_db_session()
    try:
        pay_repo = PaymentRepository(db)
        order_repo = OrderRepository(db)

        payment = pay_repo.get_by_id(payment_id)
        if not payment:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        # Verify ownership via order → user
        from backend.services.user_service import UserService
        from backend.services.order_service import OrderService
        user_service = UserService(db)
        order_service = OrderService(db)
        order = order_service.get_order_by_id(payment.order_id)
        if not order:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        user = user_service.get_user_by_id(order.user_id)
        if not user or user.telegram_user_id != callback.from_user.id:
            await callback.answer("Нет доступа.", show_alert=True)
            return

        if payment.status not in ("created", "processing"):
            await callback.answer("Заявка уже обработана.", show_alert=True)
            return

        pay_repo.update_status(payment, PaymentStatus.CANCELLED)
        order_repo.update_status(order, OrderStatus.CANCELLED)
        db.commit()

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

        await callback.message.answer(
            f"↩️ Заявка <b>#{payment_id}</b> отменена.",
            parse_mode="HTML",
        )
    except Exception as e:
        db.rollback()
        logger.error(f"cancel payment error: {e}")
        await callback.answer("Ошибка при отмене.", show_alert=True)
    finally:
        db.close()

    await callback.answer()


# ── Admin: confirm payment ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("manual_confirm:"))
async def cb_manual_confirm(callback: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    payment_id = int(callback.data.split(":")[1])

    try:
        result = await ManualPaymentService.confirm_payment(bot, payment_id)
        admin_name = callback.from_user.username or callback.from_user.first_name or "Admin"
        try:
            await callback.message.edit_text(
                callback.message.text + f"\n\n✅ Подтверждено @{admin_name}"
            )
        except Exception:
            pass
        await callback.answer(f"✅ Оплата #{payment_id} подтверждена!")
    except Exception as e:
        logger.error(f"admin confirm error: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)


# ── Admin: reject menu ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("manual_reject_menu:"))
async def cb_manual_reject_menu(callback: CallbackQuery) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    payment_id = int(callback.data.split(":")[1])
    await callback.message.answer(
        f"❌ Выберите причину отклонения заявки <b>#{payment_id}</b>:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="Перевод не найден",
                callback_data=f"manual_reject:{payment_id}:not_found"
            )],
            [InlineKeyboardButton(
                text="Неверная сумма",
                callback_data=f"manual_reject:{payment_id}:wrong_amount"
            )],
            [InlineKeyboardButton(
                text="Уточнить у менеджера",
                callback_data=f"manual_reject:{payment_id}:other"
            )],
        ])
    )
    await callback.answer()


# ── Admin: reject with reason ───────────────────────────────────────────────

@router.callback_query(F.data.startswith("manual_reject:"))
async def cb_manual_reject(callback: CallbackQuery, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":", 2)
    payment_id = int(parts[1])
    reason_key = parts[2]

    reason_texts = {
        "not_found":    "Перевод не найден на карте",
        "wrong_amount": "Неверная сумма перевода",
        "other":        "Уточните детали у менеджера",
    }
    reason = reason_texts.get(reason_key, reason_key)

    try:
        await ManualPaymentService.reject_payment(bot, payment_id, reason)
        admin_name = callback.from_user.username or callback.from_user.first_name or "Admin"
        try:
            await callback.message.edit_text(
                callback.message.text + f"\n\n❌ Отклонено @{admin_name}: {reason}"
            )
        except Exception:
            pass
        await callback.answer(f"❌ Оплата #{payment_id} отклонена")
    except Exception as e:
        logger.error(f"admin reject error: {e}")
        await callback.answer(f"Ошибка: {e}", show_alert=True)
