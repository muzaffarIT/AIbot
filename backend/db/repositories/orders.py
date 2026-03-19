from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.order import Order


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_order_number(self, order_number: str) -> Order | None:
        stmt = select(Order).where(Order.order_number == order_number)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_id(self, order_id: int) -> Order | None:
        stmt = select(Order).where(Order.id == order_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_user_orders(self, user_id: int, limit: int = 10) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create_order(
        self,
        user_id: int,
        plan_id: int,
        order_number: str,
        email: str | None,
        amount: float,
        currency: str,
        status: str,
        payment_method: str | None = None,
        external_order_id: str | None = None,
    ) -> Order:
        order = Order(
            user_id=user_id,
            plan_id=plan_id,
            order_number=order_number,
            email=email,
            amount=amount,
            currency=currency,
            status=status,
            payment_method=payment_method,
            external_order_id=external_order_id,
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def update_status(self, order: Order, status: str) -> Order:
        order.status = status
        self.db.commit()
        self.db.refresh(order)
        return order