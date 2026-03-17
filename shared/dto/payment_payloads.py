from dataclasses import dataclass


@dataclass(slots=True)
class PaymentWebhookEvent:
    provider: str
    status: str
    raw_payload: str
    payment_id: int | None = None
    provider_payment_id: str | None = None
    provider_transaction_id: str | None = None
    amount: float | None = None
    currency: str | None = None
