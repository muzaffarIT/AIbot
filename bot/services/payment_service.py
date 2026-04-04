"""
Manual card-based payment service for HARF AI.
Flow: user picks a plan → bot shows card details → user confirms payment
     → admins get notified → admin approves/rejects → credits added.
"""

import logging
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from backend.services.order_service import OrderService
from backend.services.payment_service import PaymentService
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from backend.core.config import settings
from bot.services.db_session import get_db_session

logger = logging.getLogger(__name__)

# Credit packages — price in UZS (сум), credits for HARF AI
PACKAGES = {
    "start": {
        "name": "⚡ Start",
        "description": "100 кредитов. ~20 картинок Nano Banana или 3 видео Veo fast.",
        "credits": 100,
        "price_uzs": 59_000,
        "plan_code": "start",
    },
    "pro": {
        "name": "💎 Pro",
        "description": "300 кредитов. ~60 картинок или 10 видео Veo fast. Популярный выбор.",
        "credits": 300,
        "price_uzs": 149_000,
        "plan_code": "pro",
    },
    "creator": {
        "name": "🚀 Creator",
        "description": "600 кредитов. ~120 картинок или 20 видео Veo.",
        "credits": 600,
        "price_uzs": 269_000,
        "plan_code": "creator",
    },
    "ultra": {
        "name": "👑 Ultra",
        "description": "1500 кредитов. Максимальный пакет для профессионалов.",
        "credits": 1500,
        "price_uzs": 590_000,
        "plan_code": "ultra",
    },
}


def _fmt(amount: int) -> str:
    """Format UZS amount with spaces: 149000 → '149 000'"""
    return f"{amount:,}".replace(",", " ")


class ManualPaymentService:
    """Handles the full manual payment lifecycle."""

    @staticmethod
    async def send_invoice(bot: Bot, chat_id: int, telegram_user_id: int, package_id: str) -> int | None:
        """
        Create Order + Payment records, then send card invoice to user.
        Returns payment_id or None on failure.
        """
        if package_id not in PACKAGES:
            raise ValueError(f"Unknown package: {package_id}")

        pkg = PACKAGES[package_id]
        card = settings.card_number or "—"
        owner = settings.card_owner or "—"

        db = get_db_session()
        try:
            user_service = UserService(db)
            order_service = OrderService(db)
            payment_service = PaymentService(db)

            user = user_service.get_user_by_telegram_id(telegram_user_id)
            if not user:
                user = user_service.get_or_create_user(
                    telegram_user_id=telegram_user_id,
                    username=None,
                    first_name=None,
                    last_name=None,
                )

            # Check if user already has a pending payment
            from backend.db.repositories.payments import PaymentRepository
            from backend.db.repositories.orders import OrderRepository as _OrderRepo
            from shared.enums.payment_status import PaymentStatus
            from shared.enums.order_status import OrderStatus as _OrderStatus
            from datetime import datetime, timezone, timedelta
            pay_repo = PaymentRepository(db)
            existing = pay_repo.get_pending_manual_payment(user.id)

            # Auto-cancel payments older than 24 hours
            if existing:
                age = datetime.now(timezone.utc) - existing.created_at.replace(tzinfo=timezone.utc)
                if age > timedelta(hours=24):
                    pay_repo.update_status(existing, PaymentStatus.CANCELLED)
                    order_repo2 = _OrderRepo(db)
                    order2 = order_repo2.get_by_id(existing.order_id)
                    if order2:
                        order_repo2.update_status(order2, _OrderStatus.CANCELLED)
                    db.commit()
                    existing = None

            if existing:
                await bot.send_message(
                    chat_id,
                    f"⚠️ У вас уже есть активная заявка на оплату <b>#{existing.id}</b>.\n"
                    f"Дождитесь подтверждения или отмените её.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="❌ Отменить заявку",
                            callback_data=f"manual_cancel:{existing.id}"
                        )
                    ]])
                )
                return existing.id

            order = order_service.create_order_for_plan(
                user_id=user.id,
                plan_code=pkg["plan_code"],
                payment_method="manual_card",
            )
            payment = payment_service.create_payment_for_order(
                order_id=order.id,
                provider="manual",
                method="card",
            )
            db.commit()

            price_fmt = _fmt(pkg["price_uzs"])
            visa_card = settings.visa_card_number or ""
            visa_owner = settings.visa_card_owner or ""

            cards_text = ""
            if card:
                cards_text += f"\n💳 <b>Humo / Uzcard</b>\n<code>{card}</code>\nПолучатель: <b>{owner}</b>"
            if visa_card:
                cards_text += f"\n\n💳 <b>Visa</b>\n<code>{visa_card}</code>\nПолучатель: <b>{visa_owner}</b>"
            if not cards_text:
                cards_text = "\n⚠️ Реквизиты временно не настроены. Обратитесь в поддержку."

            await bot.send_message(
                chat_id,
                f"💳 <b>Оплата — {pkg['name']}</b>\n\n"
                f"📦 {pkg['description']}\n"
                f"💰 Сумма: <b>{price_fmt} сум</b>\n"
                f"🎁 Кредиты: <b>{pkg['credits']}</b>\n"
                f"━━━━━━━━━━━━━━\n"
                f"Переведите на одну из карт:{cards_text}\n"
                f"━━━━━━━━━━━━━━\n"
                f"<i>После перевода нажмите кнопку ниже 👇</i>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="✅ Я оплатил",
                        callback_data=f"manual_paid:{payment.id}"
                    )],
                    [InlineKeyboardButton(
                        text="❌ Отмена",
                        callback_data=f"manual_cancel:{payment.id}"
                    )],
                ])
            )
            return payment.id

        except Exception as e:
            db.rollback()
            logger.error(f"ManualPaymentService.send_invoice error: {e}")
            raise
        finally:
            db.close()

    @staticmethod
    async def notify_admins_payment_submitted(bot: Bot, payment_id: int, telegram_user_id: int,
                                               user_full_name: str, username: str | None,
                                               package_id: str) -> None:
        """Notify all admins that a user claims to have paid."""
        pkg = PACKAGES.get(package_id, {})
        pkg_name = pkg.get("name", "?")
        price_fmt = _fmt(pkg.get("price_uzs", 0))
        uname = f"@{username}" if username else "—"

        for admin_id in settings.admin_ids_list:
            try:
                await bot.send_message(
                    admin_id,
                    f"⚡ <b>НОВАЯ ОПЛАТА #{payment_id}</b>\n\n"
                    f"👤 {user_full_name}\n"
                    f"🔗 {uname}\n"
                    f"🆔 <code>{telegram_user_id}</code>\n\n"
                    f"📦 {pkg_name}\n"
                    f"💰 {price_fmt} сум\n\n"
                    f"Проверь карту и нажми кнопку:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="✅ Подтвердить",
                            callback_data=f"manual_confirm:{payment_id}"
                        ),
                        InlineKeyboardButton(
                            text="❌ Отклонить",
                            callback_data=f"manual_reject_menu:{payment_id}"
                        ),
                    ]])
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

    @staticmethod
    async def confirm_payment(bot: Bot, payment_id: int) -> dict:
        """Admin confirmed the payment — credit user and notify them."""
        db = get_db_session()
        try:
            payment_service = PaymentService(db)
            order_service = OrderService(db)
            balance_service = BalanceService(db)

            payment = payment_service.confirm_payment(payment_id)
            order = order_service.get_order_by_id(payment.order_id)
            if not order:
                raise ValueError("Order not found")

            from backend.db.repositories.plans import PlanRepository
            plan_repo = PlanRepository(db)
            plan = plan_repo.get_by_id(order.plan_id)

            balance = balance_service.get_balance_value(order.user_id)

            # Get telegram_user_id
            user_service = UserService(db)
            user = user_service.get_user_by_id(order.user_id)

            db.commit()

            if user:
                credits = plan.credits_amount if plan else 0
                try:
                    await bot.send_message(
                        user.telegram_user_id,
                        f"✅ <b>Оплата подтверждена!</b>\n\n"
                        f"📦 {plan.name if plan else 'Пакет'}\n"
                        f"💰 Начислено: <b>{credits}</b> кредитов\n"
                        f"💳 Текущий баланс: <b>{balance}</b> кредитов\n\n"
                        f"Спасибо! Теперь создавай нейроарт 🎨",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user {user.telegram_user_id}: {e}")

                # Check and award achievements after payment
                try:
                    from bot.services.achievements import check_and_award_achievements
                    newly_awarded = check_and_award_achievements(
                        db=db,
                        user_id=order.user_id,
                        telegram_id=user.telegram_user_id,
                        lang=user.language_code or "ru",
                    )
                    db.commit()
                    for ach, bonus in newly_awarded:
                        try:
                            await bot.send_message(
                                user.telegram_user_id,
                                f"🏆 <b>Достижение разблокировано!</b>\n\n"
                                f"{ach.emoji} <b>{ach.name_ru}</b>\n"
                                f"{ach.description_ru}\n"
                                f"💰 +{bonus} кредитов",
                                parse_mode="HTML",
                            )
                        except Exception:
                            pass
                except Exception as e:
                    logger.error(f"Achievement check error after payment: {e}")

            # Log to Google Sheets
            if user and plan:
                try:
                    from bot.services.sheets import log_payment_confirmed
                    log_payment_confirmed(
                        payment_id=payment_id,
                        user_full_name=user.first_name or "—",
                        username=user.username,
                        telegram_id=user.telegram_user_id,
                        plan_name=plan.name,
                        amount_uzs=int(payment.amount),
                    )
                except Exception as e:
                    logger.error(f"Sheets log error (confirm): {e}")

            return {"payment_id": payment_id, "balance": balance}

        except Exception as e:
            db.rollback()
            logger.error(f"confirm_payment error: {e}")
            raise
        finally:
            db.close()

    @staticmethod
    async def reject_payment(bot: Bot, payment_id: int, reason: str) -> None:
        """Admin rejected the payment — cancel and notify user."""
        db = get_db_session()
        try:
            from backend.db.repositories.payments import PaymentRepository
            from backend.db.repositories.orders import OrderRepository
            from shared.enums.payment_status import PaymentStatus
            from shared.enums.order_status import OrderStatus

            pay_repo = PaymentRepository(db)
            order_repo = OrderRepository(db)

            payment = pay_repo.get_by_id(payment_id)
            if not payment:
                raise ValueError("Payment not found")

            pay_repo.update_status(payment, PaymentStatus.FAILED)
            order = order_repo.get_by_id(payment.order_id)
            if order:
                order_repo.update_status(order, OrderStatus.CANCELLED)

            user_service = UserService(db)
            order_service = OrderService(db)
            ord_ = order_service.get_order_by_id(payment.order_id)
            user = user_service.get_user_by_id(ord_.user_id) if ord_ else None

            db.commit()

            if user:
                try:
                    await bot.send_message(
                        user.telegram_user_id,
                        f"❌ <b>Оплата #{payment_id} отклонена</b>\n\n"
                        f"Причина: {reason}\n\n"
                        f"Если это ошибка, обратитесь в поддержку: @{settings.support_username}",
                        parse_mode="HTML",
                    )
                except Exception as e:
                    logger.error(f"Failed to notify user on rejection: {e}")

            # Log to Google Sheets
            if user:
                try:
                    from bot.services.sheets import log_payment_rejected
                    from backend.db.repositories.plans import PlanRepository
                    plan_name = "—"
                    if ord_:
                        plan = PlanRepository(db).get_by_id(ord_.plan_id)
                        plan_name = plan.name if plan else "—"
                    log_payment_rejected(
                        payment_id=payment_id,
                        user_full_name=user.first_name or "—",
                        username=user.username,
                        telegram_id=user.telegram_user_id,
                        plan_name=plan_name,
                        amount_uzs=int(payment.amount),
                        reason=reason,
                    )
                except Exception as e:
                    logger.error(f"Sheets log error (reject): {e}")

        except Exception as e:
            db.rollback()
            logger.error(f"reject_payment error: {e}")
            raise
        finally:
            db.close()
