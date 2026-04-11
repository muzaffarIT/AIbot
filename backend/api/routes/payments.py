import logging

import httpx
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.core.config import settings
from backend.core.security import verify_telegram_data
from backend.services.payment_service import PaymentService
from backend.services.order_service import OrderService
from backend.services.user_service import UserService
from backend.db.repositories.payments import PaymentRepository
from shared.enums.payment_status import PaymentStatus

logger = logging.getLogger(__name__)
router = APIRouter()


def _require_tg_auth(
    authorization: str | None = Header(default=None),
    x_telegram_init_data: str | None = Header(default=None),
) -> dict:
    """Validate Telegram WebApp initData.
    Accepts either:
      - Authorization: tma <initData>   (sent by miniapp)
      - X-Telegram-Init-Data: <initData>  (alternative)
    """
    init_data: str | None = None
    if authorization and authorization.lower().startswith("tma "):
        init_data = authorization[4:].strip()
    elif x_telegram_init_data:
        init_data = x_telegram_init_data

    if not init_data:
        raise HTTPException(status_code=401, detail="Missing Telegram auth header")
    return verify_telegram_data(init_data)


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

        # Auto-cancel stale or non-submitted pending payments
        from datetime import datetime, timezone, timedelta
        from shared.enums.order_status import OrderStatus as _OS
        from backend.db.repositories.orders import OrderRepository as _OR2
        stale = pay_repo.get_pending_manual_payment(user.id)
        if stale:
            age = datetime.now(timezone.utc) - stale.created_at.replace(tzinfo=timezone.utc)
            stale_order = _OR2(db).get_by_id(stale.order_id)
            if age > timedelta(hours=24) or stale.status == PaymentStatus.CREATED:
                # Cancel: either too old, or user never submitted payment (CREATED state = not yet claimed paid)
                pay_repo.update_status(stale, PaymentStatus.CANCELLED)
                if stale_order:
                    _OR2(db).update_status(stale_order, _OS.CANCELLED)
                db.commit()
                stale = None

        # Only block on PROCESSING payments (user claimed they paid, awaiting admin review)
        existing = stale
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
async def notify_paid(
    payment_id: int,
    db: Session = Depends(get_db),
) -> dict:
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


@router.get("/card-details")
def get_card_details() -> dict:
    """Return card details for manual UZS top-up (shown in miniapp)."""
    return {
        "card_number": settings.card_number or "",
        "card_owner": settings.card_owner or "",
        "visa_card_number": settings.visa_card_number or "",
        "visa_card_owner": settings.visa_card_owner or "",
    }


class UzsTopupNotifyRequest(BaseModel):
    telegram_user_id: int
    amount: int  # in sums


@router.post("/uzs-topup-notify")
async def uzs_topup_notify(
    payload: UzsTopupNotifyRequest,
    db: Session = Depends(get_db),
) -> dict:
    """User claims they paid for UZS balance top-up. Notify admins via bot."""
    import json as _json

    user_service = UserService(db)
    user = user_service.get_user_by_telegram_id(payload.telegram_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    full_name = user.first_name or "—"
    uname = f"@{user.username}" if user.username else "—"
    amount_fmt = f"{payload.amount:,}".replace(",", " ")
    tg_id = payload.telegram_user_id

    confirm_kb = _json.dumps({"inline_keyboard": [[
        {"text": "✅ Подтвердить", "callback_data": f"uzs_ok:{tg_id}:{payload.amount}"},
        {"text": "❌ Отклонить",   "callback_data": f"uzs_no:{tg_id}"},
    ]]})

    notify_chat = (settings.payment_notify_chat_id or "").strip()
    recipients = [int(notify_chat)] if notify_chat else list(settings.admin_ids_list)
    bot_token = (settings.bot_token or "").strip()

    tg_errors = []
    if bot_token and recipients:
        for chat_id in recipients:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": (
                                f"💵 <b>ПОПОЛНЕНИЕ БАЛАНСА (СУМ)</b>\n\n"
                                f"👤 {full_name}\n"
                                f"🔗 {uname}\n"
                                f"🆔 <code>{tg_id}</code>\n\n"
                                f"💰 Сумма: <b>{amount_fmt} сум</b>\n\n"
                                f"Проверь карту и нажми кнопку:"
                            ),
                            "parse_mode": "HTML",
                            "reply_markup": confirm_kb,
                        },
                    )
                    if not resp.is_success:
                        tg_errors.append(f"chat {chat_id}: {resp.text}")
            except Exception as e:
                tg_errors.append(str(e))
    else:
        logger.warning("uzs_topup_notify: no bot_token or admin recipients configured")

    result: dict = {"ok": True, "amount": payload.amount}
    if tg_errors:
        result["warnings"] = tg_errors
    return result


class PayFromBalanceRequest(BaseModel):
    telegram_user_id: int
    plan_code: str


@router.post("/pay-from-balance")
def pay_from_balance(payload: PayFromBalanceRequest, db: Session = Depends(get_db)) -> dict:
    """Pay for a plan directly from UZS wallet balance."""
    try:
        from backend.db.repositories.plans import PlanRepository
        from backend.services.order_service import OrderService
        from shared.enums.order_status import OrderStatus

        user_service = UserService(db)
        balance_service = PaymentService(db).balance_service
        order_service = OrderService(db)
        payment_service = PaymentService(db)
        plan_repo = PlanRepository(db)

        user = user_service.get_user_by_telegram_id(payload.telegram_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        plan = plan_repo.get_by_code(payload.plan_code)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail="Plan not found")

        plan_price = int(plan.price)

        # Lock the user row to prevent concurrent double-spend
        from backend.models.user import User as _User
        user = db.query(_User).with_for_update().filter(_User.id == user.id).first()
        uzs_balance = getattr(user, "uzs_balance", 0) or 0
        if uzs_balance < plan_price:
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно средств: {uzs_balance} < {plan_price}"
            )

        # Deduct from UZS wallet
        user.uzs_balance = uzs_balance - plan_price
        db.flush()

        # Create order + payment and immediately confirm
        order = order_service.create_order_for_plan(
            user_id=user.id,
            plan_code=payload.plan_code,
            payment_method="uzs_balance",
        )
        payment = payment_service.create_payment_for_order(
            order_id=order.id,
            provider="uzs_balance",
            method="balance",
        )
        confirmed = payment_service.confirm_payment(payment.id)
        db.flush()

        from backend.services.balance_service import BalanceService
        new_credits = BalanceService(db).get_balance_value(user.id)
        db.commit()

        try:
            from bot.services.sheets import log_balance_payment
            log_balance_payment(
                user_full_name=user.first_name or "—",
                username=user.username,
                telegram_id=user.telegram_user_id,
                plan_name=plan.name,
                amount_uzs=plan_price,
                credits=plan.credits_amount,
            )
        except Exception as _se:
            logger.warning(f"[SHEETS] balance payment log failed: {_se}")

        return {
            "success": True,
            "plan_name": plan.name,
            "plan_code": plan.code,
            "credits_added": plan.credits_amount,
            "new_credits_balance": new_credits,
            "new_uzs_balance": user.uzs_balance,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"pay_from_balance error: {e}")
        raise HTTPException(status_code=500, detail="Ошибка оплаты с баланса")
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
