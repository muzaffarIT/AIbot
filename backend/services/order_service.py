from sqlalchemy.orm import Session

from backend.db.repositories.orders import OrderRepository
from backend.db.repositories.plans import PlanRepository
from backend.models.order import Order
from shared.enums.order_status import OrderStatus
from shared.utils.helpers import generate_order_number


class OrderService:
    def __init__(self, db: Session) -> None:
        self.repo = OrderRepository(db)
        self.plan_repo = PlanRepository(db)

    def create_order_for_plan(
        self,
        user_id: int,
        plan_code: str,
        email: str | None = None,
        payment_method: str | None = None,
    ) -> Order:
        plan = self.plan_repo.get_by_code(plan_code)
        if not plan:
            raise ValueError("Plan not found")
        if not plan.is_active:
            raise ValueError("Plan is inactive")

        order_number = generate_order_number()

        return self.repo.create_order(
            user_id=user_id,
            plan_id=plan.id,
            order_number=order_number,
            email=email,
            amount=plan.price,
            currency=plan.currency,
            status=OrderStatus.PENDING,
            payment_method=payment_method,
            external_order_id=None,
        )

    def get_user_orders(self, user_id: int, limit: int = 10) -> list[Order]:
        return self.repo.get_user_orders(user_id=user_id, limit=limit)

    def mark_order_waiting_payment(self, order_id: int) -> Order:
        order = self.repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        if order.status == OrderStatus.PAID:
            return order

        return self.repo.update_status(order, OrderStatus.WAITING_PAYMENT)

    def mark_order_paid(self, order_id: int) -> Order:
        order = self.repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        return self.repo.update_status(order, OrderStatus.PAID)

    def mark_order_cancelled(self, order_id: int) -> Order:
        order = self.repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        return self.repo.update_status(order, OrderStatus.CANCELLED)

    def mark_order_failed(self, order_id: int) -> Order:
        order = self.repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        return self.repo.update_status(order, OrderStatus.FAILED)

    def get_order_by_id(self, order_id: int) -> Order | None:
        return self.repo.get_by_id(order_id)
