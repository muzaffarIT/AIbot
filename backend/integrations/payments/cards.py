from typing import Any

from backend.core.config import settings
from backend.integrations.payments.base import BasePaymentProvider, PaymentProviderError
from shared.dto.payment_payloads import PaymentWebhookEvent
from shared.enums.providers import PaymentProvider


class CardsPaymentProvider(BasePaymentProvider):
    provider_name = PaymentProvider.CARDS
    secret_headers = ("x-cards-secret", "x-webhook-secret")

    def __init__(self) -> None:
        super().__init__(settings.cards_provider_secret)

    def _build_event(
        self,
        payload: dict[str, Any],
        raw_payload: str,
    ) -> PaymentWebhookEvent:
        payment_id = self._coerce_int(payload.get("payment_id") or payload.get("id"))
        provider_payment_id = payload.get("provider_payment_id")
        if payment_id is None and not provider_payment_id:
            raise PaymentProviderError("Payment identifier is missing")

        return PaymentWebhookEvent(
            provider=self.provider_name,
            status=self._status_from_raw(payload.get("status", "paid")),
            payment_id=payment_id,
            provider_payment_id=str(provider_payment_id) if provider_payment_id else None,
            provider_transaction_id=str(payload.get("transaction_id")) if payload.get("transaction_id") else None,
            amount=self._coerce_float(payload.get("amount")),
            currency=str(payload.get("currency")) if payload.get("currency") else None,
            raw_payload=self._dump_payload(payload, raw_payload),
        )
