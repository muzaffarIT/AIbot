import logging

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.config import settings
from backend.services.payment_service import PaymentService
from backend.services.order_service import OrderService
from backend.services.user_service import UserService
from backend.db.repositories.payments import PaymentRepository
from shared.enums.payment_status import PaymentStatus

logger = logging.getLogger(__name__)
router = APIRouter()


class CreatePaymentRequest(BaseModel):
    order_id: int
    provider: str
    method: str


def serialize_payment(payment) -> dict:
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "provider": payment.provider,
        "method": payment.method,
        "amount": payment.amount,
        "currency": payment.currency,
        "status": payment.status,
        "provider_payment_id": payment.provider_payment_id,
        "provider_transaction_id": payment.provider_transaction_id,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
    }


@router.post("/")
def create_payment(payload: CreatePaymentRequest, db: Session = Depends(get_db)) -> dict:
    try:
        payment_service = PaymentService(db)

        payment = payment_service.create_payment_for_order(
            order_id=payload.order_id,
            provider=payload.provider,
            method=payload.method,
        )

        return serialize_payment(payment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        db.close()


@router.get("/order/{order_id}")
def get_order_payments(order_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        payment_service = PaymentService(db)
        payments = payment_service.get_order_payments(order_id)

        return {
            "order_id": order_id,
            "payments": [serialize_payment(payment) for payment in payments],
        }
    finally:
        db.close()


@router.post("/{payment_id}/confirm")
def confirm_payment(payment_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        payment_service = PaymentService(db)
        payment = payment_service.confirm_payment(payment_id)
        order = payment_service.order_repo.get_by_id(payment.order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        plan = payment_service.plan_repo.get_by_id(order.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        balance = payment_service.balance_service.get_balance_value(order.user_id)

        return {
            **serialize_payment(payment),
            "order_status": order.status,
            "credited_amount": plan.credits_amount,
            "current_balance": balance,
            "plan_code": plan.code,
            "plan_name": plan.name,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        db.close()


class CreateManualPaymentRequest(BaseModel):
    telegram_user_id: int
    plan_code: str


@router.post("/create-manual")
def create_manual_payment(payload: CreateManualPaymentRequest, db: Session = Depends(get_db)) -> dict:
    """Create order + payment for manual card flow. Returns card details."""
    try:
        user_service = UserService(db)
        order_service = OrderService(db)
        payment_service = PaymentService(db)
        pay_repo = PaymentRepository(db)

        user = user_service.get_user_by_telegram_id(payload.telegram_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Return existing pending payment instead of creating duplicate
        existing = pay_repo.get_pending_manual_payment(user.id)
        if existing:
            from backend.db.repositories.orders import OrderRepository
            from backend.db.repositories.plans import PlanRepository
            order_repo = OrderRepository(db)
            plan_repo = PlanRepository(db)
            order = order_repo.get_by_id(existing.order_id)
            plan = plan_repo.get_by_id(order.plan_id) if order else None
            return {
                "payment_id": existing.id,
                "order_id": order.id if order else None,
                "order_number": order.order_number if order else None,
                "amount": existing.amount,
                "currency": existing.currency,
                "credits": plan.credits_amount if plan else 0,
                "plan_name": plan.name if plan else None,
                "plan_code": plan.code if plan else None,
                "card_number": settings.card_number or "",
                "card_owner": settings.card_owner or "",
                "visa_card_number": settings.visa_card_number or "",
                "visa_card_owner": settings.visa_card_owner or "",
                "already_pending": True,
            }

        order = order_service.create_order_for_plan(
            user_id=user.id,
            plan_code=payload.plan_code,
            payment_method="manual_card",
        )
        payment = payment_service.create_payment_for_order(
            order_id=order.id,
            provider="manual",
            method="card",
        )
        db.commit()

        from backend.db.repositories.plans import PlanRepository
        plan = PlanRepository(db).get_by_id(order.plan_id)

        return {
            "payment_id": payment.id,
            "order_id": order.id,
            "order_number": order.order_number,
            "amount": payment.amount,
            "currency": payment.currency,
            "credits": plan.credits_amount if plan else 0,
            "plan_name": plan.name if plan else None,
            "plan_code": plan.code if plan else None,
            "card_number": settings.card_number or "",
            "card_owner": settings.card_owner or "",
            "visa_card_number": settings.visa_card_number or "",
            "visa_card_owner": settings.visa_card_owner or "",
            "already_pending": False,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"create_manual_payment error: {e}")
        raise HTTPException(status_code=500, detail="Не удалось создать заявку")
    finally:
        db.close()


@router.post("/{payment_id}/notify-paid")
async def notify_paid(payment_id: int, db: Session = Depends(get_db)) -> dict:
    """User claims they paid. Mark as processing and notify admins via Telegram."""
    try:
        pay_repo = PaymentRepository(db)
        payment = pay_repo.get_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if payment.status == PaymentStatus.PAID:
            return {"status": "already_paid"}

        if payment.status not in (PaymentStatus.CREATED, PaymentStatus.PROCESSING):
            raise HTTPException(status_code=400, detail="Payment cannot be notified")

        pay_repo.update_status(payment, PaymentStatus.PROCESSING)
        db.commit()

        from backend.db.repositories.orders import OrderRepository
        from backend.db.repositories.plans import PlanRepository
        order_repo = OrderRepository(db)
        plan_repo = PlanRepository(db)

        order = order_repo.get_by_id(payment.order_id)
        plan = plan_repo.get_by_id(order.plan_id) if order else None
        user = UserService(db).get_user_by_id(order.user_id) if order else None

        if not settings.bot_token:
            logger.error("notify_paid: BOT_TOKEN not configured in environment")
            return {"status": "notified", "payment_id": payment_id, "warn": "BOT_TOKEN missing"}

        # Determine recipients: group chat takes priority over individual admin IDs
        notify_chat_id = settings.payment_notify_chat_id.strip() if settings.payment_notify_chat_id else ""
        recipient_ids: list = [int(notify_chat_id)] if notify_chat_id else list(settings.admin_ids_list)

        if not recipient_ids:
            logger.error("notify_paid: neither PAYMENT_NOTIFY_CHAT_ID nor ADMIN_IDS configured")
            return {"status": "notified", "payment_id": payment_id, "warn": "no recipients configured"}

        bot_token = settings.bot_token.strip()
        tg_errors = []

        if user:
            plan_name = plan.name if plan else "—"
            amount_fmt = f"{int(payment.amount):,}".replace(",", " ")
            uname = f"@{user.username}" if user.username else "—"
            full_name = user.first_name or "—"
            import json as _json
            confirm_kb = _json.dumps({"inline_keyboard": [[
                {"text": "✅ Подтвердить", "callback_data": f"manual_confirm:{payment_id}"},
                {"text": "❌ Отклонить", "callback_data": f"manual_reject_menu:{payment_id}"},
            ]]})
            for chat_id in recipient_ids:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        resp = await client.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": (
                                    f"⚡ <b>НОВАЯ ОПЛАТА #{payment_id}</b>\n\n"
                                    f"👤 {full_name}\n"
                                    f"🔗 {uname}\n"
                                    f"🆔 <code>{user.telegram_user_id}</code>\n\n"
                                    f"📦 {plan_name}\n"
                                    f"💰 {amount_fmt} сум\n\n"
                                    f"Проверь карту и нажми кнопку:"
                                ),
                                "parse_mode": "HTML",
                                "reply_markup": confirm_kb,
                            },
                        )
                        if not resp.is_success:
                            err = f"chat {chat_id}: {resp.text}"
                            logger.error(f"Telegram API error — {err}")
                            tg_errors.append(err)
                except Exception as e:
                    err = f"chat {chat_id}: {e}"
                    logger.error(f"Failed to notify — {err}")
                    tg_errors.append(err)

        result: dict = {"status": "notified", "payment_id": payment_id}
        if tg_errors:
            result["tg_errors"] = tg_errors
        return result
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"notify_paid error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка уведомления")
    finally:
        db.close()


@router.post("/{payment_id}/cancel")
def cancel_payment(payment_id: int, db: Session = Depends(get_db)) -> dict:
    """User cancels their own pending payment."""
    try:
        from backend.db.repositories.orders import OrderRepository
        from shared.enums.order_status import OrderStatus

        pay_repo = PaymentRepository(db)
        order_repo = OrderRepository(db)

        payment = pay_repo.get_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if payment.status not in (PaymentStatus.CREATED, PaymentStatus.PROCESSING):
            raise HTTPException(status_code=400, detail="Cannot cancel payment in this state")

        pay_repo.update_status(payment, PaymentStatus.CANCELLED)
        order = order_repo.get_by_id(payment.order_id)
        if order:
            order_repo.update_status(order, OrderStatus.CANCELLED)
        db.commit()

        return {"status": "cancelled", "payment_id": payment_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"cancel_payment error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка отмены")
    finally:
        db.close()
