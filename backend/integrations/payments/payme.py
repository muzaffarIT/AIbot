from typing import Any

from backend.core.config import settings
from backend.integrations.payments.base import BasePaymentProvider, PaymentProviderError
from shared.dto.payment_payloads import PaymentWebhookEvent
from shared.enums.providers import PaymentProvider


class PaymePaymentProvider(BasePaymentProvider):
    provider_name = PaymentProvider.PAYME
    secret_headers = ("x-payme-secret", "x-webhook-secret")

    def __init__(self) -> None:
        super().__init__(settings.payme_secret_key)

    def _build_event(
        self,
        payload: dict[str, Any],
        raw_payload: str,
    ) -> PaymentWebhookEvent:
        params = payload.get("params")
        data = params if isinstance(params, dict) else payload
        account = data.get("account") if isinstance(data.get("account"), dict) else {}

        payment_id = self._coerce_int(
            data.get("payment_id")
            or account.get("payment_id")
            or payload.get("payment_id")
        )
        provider_payment_id = payload.get("id") or data.get("provider_payment_id")
        provider_transaction_id = data.get("transaction_id") or data.get("transaction")
        raw_status = data.get("status", payload.get("status", data.get("state", payload.get("state", "paid"))))

        if payment_id is None and not provider_payment_id:
            raise PaymentProviderError("Payment identifier is missing")

        return PaymentWebhookEvent(
            provider=self.provider_name,
            status=self._status_from_raw(raw_status),
            payment_id=payment_id,
            provider_payment_id=str(provider_payment_id) if provider_payment_id else None,
            provider_transaction_id=str(provider_transaction_id) if provider_transaction_id else None,
            amount=self._coerce_float(data.get("amount")),
            currency=str(data.get("currency")) if data.get("currency") else None,
            raw_payload=self._dump_payload(payload, raw_payload),
        )
