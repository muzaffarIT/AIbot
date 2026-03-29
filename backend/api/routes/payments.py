from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services.payment_service import PaymentService

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
