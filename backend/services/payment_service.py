from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.repositories.orders import OrderRepository
from backend.db.repositories.payments import PaymentRepository
from backend.db.repositories.plans import PlanRepository
from backend.models.payment import Payment
from backend.models.credit_transaction import CreditTransaction
from shared.dto.payment_payloads import PaymentWebhookEvent
from shared.enums.payment_status import PaymentStatus
from shared.enums.credit_transaction_type import CreditTransactionType
from backend.services.balance_service import BalanceService
from backend.services.order_service import OrderService


class PaymentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PaymentRepository(db)
        self.order_repo = OrderRepository(db)
        self.plan_repo = PlanRepository(db)
        self.balance_service = BalanceService(db)
        self.order_service = OrderService(db)

    def create_payment_for_order(
        self,
        order_id: int,
        provider: str,
        method: str,
    ) -> Payment:
        order = self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        existing_payment = self.repo.get_latest_by_order_id(order.id)
        if existing_payment and existing_payment.status in (
            PaymentStatus.CREATED,
            PaymentStatus.PROCESSING,
            PaymentStatus.PAID,
        ):
            if existing_payment.status != PaymentStatus.PAID:
                self.order_service.mark_order_waiting_payment(order.id)
            return existing_payment

        payment = self.repo.create_payment(
            order_id=order.id,
            provider=provider,
            method=method,
            amount=order.amount,
            currency=order.currency,
            status=PaymentStatus.CREATED,
        )
        payment = self.repo.update_payment(
            payment,
            provider_payment_id=f"{provider}-{payment.id}",
        )
        self.order_service.mark_order_waiting_payment(order.id)
        return payment

    def get_order_payments(self, order_id: int) -> list[Payment]:
        return self.repo.get_by_order_id(order_id)

    def _get_plan_for_payment(self, payment: Payment):
        order = self.order_repo.get_by_id(payment.order_id)
        if not order:
            raise ValueError("Order not found")

        plan = self.plan_repo.get_by_id(order.plan_id)
        if plan is None:
            raise ValueError("Plan not found")
        return order, plan

    def _resolve_payment_from_event(self, event: PaymentWebhookEvent) -> Payment:
        payment = None
        if event.payment_id is not None:
            payment = self.repo.get_by_id(event.payment_id)
        if payment is None and event.provider_payment_id:
            payment = self.repo.get_by_provider_payment_id(event.provider_payment_id)
        if payment is None and event.provider_transaction_id:
            payment = self.repo.get_by_provider_transaction_id(event.provider_transaction_id)
        if payment is None:
            raise ValueError("Payment not found")
        if payment.provider != event.provider:
            raise ValueError("Provider mismatch")
        return payment

    def confirm_payment(self, payment_id: int) -> Payment:
        payment = self.repo.get_by_id(payment_id)
        if not payment:
            raise ValueError("Payment not found")

        if payment.status == PaymentStatus.PAID:
            return payment

        order, plan = self._get_plan_for_payment(payment)

        updated_payment = self.repo.update_status(payment, PaymentStatus.PAID)
        self.order_service.mark_order_paid(order.id)

        # Double payment protection: skip if credits were already added for this payment
        already_credited = self.db.execute(
            select(CreditTransaction).where(
                CreditTransaction.reference_type == "payment",
                CreditTransaction.reference_id == str(updated_payment.id),
            )
        ).scalar_one_or_none()

        if not already_credited:
            self.balance_service.add_credits(
                user_id=order.user_id,
                amount=plan.credits_amount,
                transaction_type=CreditTransactionType.TOPUP,
                reference_type="payment",
                reference_id=str(updated_payment.id),
                comment=f"Credits added after successful payment for plan {plan.code}",
            )

            # Referral commission: 10% of payment amount in UZS credited to referrer's wallet
            try:
                from backend.models.user import User as _User
                payer = self.db.query(_User).filter(_User.id == order.user_id).first()
                if payer and payer.referred_by_telegram_id:
                    referrer = self.db.query(_User).filter(
                        _User.telegram_user_id == payer.referred_by_telegram_id
                    ).first()
                    if referrer:
                        uzs_commission = max(100, int(float(updated_payment.amount) * 0.10))
                        referrer.referral_earnings = (referrer.referral_earnings or 0) + uzs_commission
                        referrer.uzs_balance = (getattr(referrer, "uzs_balance", 0) or 0) + uzs_commission
                        self.db.flush()
            except Exception:
                pass  # non-fatal — commission missed, but payment still succeeds

        return updated_payment

    def process_webhook_event(self, event: PaymentWebhookEvent) -> Payment:
        payment = self._resolve_payment_from_event(event)
        payment = self.repo.update_payment(
            payment,
            provider_payment_id=event.provider_payment_id or payment.provider_payment_id,
            provider_transaction_id=event.provider_transaction_id,
            raw_payload=event.raw_payload,
        )

        if event.status == PaymentStatus.PAID:
            return self.confirm_payment(payment.id)

        if event.status == PaymentStatus.PROCESSING:
            self.order_service.mark_order_waiting_payment(payment.order_id)
            return self.repo.update_status(payment, PaymentStatus.PROCESSING)

        if event.status == PaymentStatus.CREATED:
            self.order_service.mark_order_waiting_payment(payment.order_id)
            return self.repo.update_status(payment, PaymentStatus.CREATED)

        if event.status == PaymentStatus.CANCELLED:
            self.order_service.mark_order_cancelled(payment.order_id)
            return self.repo.update_status(payment, PaymentStatus.CANCELLED)

        if event.status == PaymentStatus.FAILED:
            self.order_service.mark_order_failed(payment.order_id)
            return self.repo.update_status(payment, PaymentStatus.FAILED)

        if event.status == PaymentStatus.REFUNDED:
            return self.repo.update_status(payment, PaymentStatus.REFUNDED)

        raise ValueError("Unsupported payment status")
