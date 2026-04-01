from datetime import datetime, timezone

from sqlalchemy import select, join
from sqlalchemy.orm import Session

from backend.models.payment import Payment
from backend.models.order import Order


class PaymentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, payment_id: int) -> Payment | None:
        stmt = select(Payment).where(Payment.id == payment_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_provider_payment_id(self, provider_payment_id: str) -> Payment | None:
        stmt = select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_provider_transaction_id(self, provider_transaction_id: str) -> Payment | None:
        stmt = select(Payment).where(Payment.provider_transaction_id == provider_transaction_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_by_order_id(self, order_id: int) -> Payment | None:
        stmt = (
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.id.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order_id(self, order_id: int) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.id.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create_payment(
        self,
        order_id: int,
        provider: str,
        method: str,
        amount: float,
        currency: str,
        status: str,
        provider_payment_id: str | None = None,
        provider_transaction_id: str | None = None,
        raw_payload: str | None = None,
    ) -> Payment:
        payment = Payment(
            order_id=order_id,
            provider=provider,
            method=method,
            amount=amount,
            currency=currency,
            status=status,
            provider_payment_id=provider_payment_id,
            provider_transaction_id=provider_transaction_id,
            raw_payload=raw_payload,
        )
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update_payment(
        self,
        payment: Payment,
        *,
        status: str | None = None,
        provider_payment_id: str | None = None,
        provider_transaction_id: str | None = None,
        raw_payload: str | None = None,
    ) -> Payment:
        if status is not None:
            payment.status = status
        if provider_payment_id is not None:
            payment.provider_payment_id = provider_payment_id
        if provider_transaction_id is not None:
            payment.provider_transaction_id = provider_transaction_id
        if raw_payload is not None:
            payment.raw_payload = raw_payload
        if status == "paid":
            payment.paid_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    def update_status(self, payment: Payment, status: str) -> Payment:
        return self.update_payment(payment, status=status)

    def get_pending_manual_payment(self, user_id: int) -> Payment | None:
        """Return the latest pending manual payment for a user, if any."""
        stmt = (
            select(Payment)
            .join(Order, Payment.order_id == Order.id)
            .where(
                Order.user_id == user_id,
                Payment.provider == "manual",
                Payment.status.in_(("created", "processing")),
            )
            .order_by(Payment.id.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()
