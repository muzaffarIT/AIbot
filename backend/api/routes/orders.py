from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.db.repositories.plans import PlanRepository
from backend.services.user_service import UserService
from backend.services.order_service import OrderService

router = APIRouter()


class CreateOrderRequest(BaseModel):
    telegram_user_id: int
    plan_code: str
    email: str | None = None
    payment_method: str | None = None


def serialize_order(order, plan_name: str | None = None, plan_code: str | None = None) -> dict:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "user_id": order.user_id,
        "plan_id": order.plan_id,
        "plan_name": plan_name,
        "plan_code": plan_code,
        "amount": order.amount,
        "currency": order.currency,
        "status": order.status,
        "payment_method": order.payment_method,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


@router.get("/telegram/{telegram_user_id}")
def get_user_orders(telegram_user_id: int, limit: int = Query(default=10, ge=1, le=50), db: Session = Depends(get_db)) -> dict:
    try:
        user_service = UserService(db)
        order_service = OrderService(db)
        plan_repo = PlanRepository(db)

        user = user_service.get_user_by_telegram_id(telegram_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        orders = order_service.get_user_orders(user_id=user.id, limit=limit)
        serialized_orders = []
        for order in orders:
            plan = plan_repo.get_by_id(order.plan_id)
            serialized_orders.append(
                serialize_order(
                    order,
                    plan_name=plan.name if plan else None,
                    plan_code=plan.code if plan else None,
                )
            )

        return {
            "user_id": user.id,
            "telegram_user_id": user.telegram_user_id,
            "orders": serialized_orders,
        }
    finally:
        db.close()


@router.post("/")
def create_order(payload: CreateOrderRequest, db: Session = Depends(get_db)) -> dict:
    try:
        user_service = UserService(db)
        order_service = OrderService(db)

        user = user_service.get_user_by_telegram_id(payload.telegram_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        order = order_service.create_order_for_plan(
            user_id=user.id,
            plan_code=payload.plan_code,
            email=payload.email,
            payment_method=payload.payment_method,
        )

        return serialize_order(order)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    finally:
        db.close()
