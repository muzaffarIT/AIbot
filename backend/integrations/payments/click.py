from typing import Any

from backend.core.config import settings
from backend.integrations.payments.base import BasePaymentProvider, PaymentProviderError
from shared.dto.payment_payloads import PaymentWebhookEvent
from shared.enums.providers import PaymentProvider


class ClickPaymentProvider(BasePaymentProvider):
    provider_name = PaymentProvider.CLICK
    secret_headers = ("x-click-secret", "x-webhook-secret")

    def __init__(self) -> None:
        super().__init__(settings.click_secret_key)

    def _build_event(
        self,
        payload: dict[str, Any],
        raw_payload: str,
    ) -> PaymentWebhookEvent:
        payment_id = self._coerce_int(
            payload.get("payment_id")
            or payload.get("merchant_prepare_id")
            or payload.get("merchant_trans_id")
        )
        provider_payment_id = payload.get("provider_payment_id") or payload.get("service_payment_id")
        provider_transaction_id = payload.get("click_trans_id") or payload.get("transaction_id")

        error_code = payload.get("error")
        raw_status = payload.get("status")
        if raw_status is None and error_code not in (None, "", "0", 0):
            raw_status = "failed"
        if raw_status is None and payload.get("action") in {"prepare", "1"}:
            raw_status = "processing"
        if raw_status is None and payload.get("action") in {"complete", "2"}:
            raw_status = "paid"
        if raw_status is None:
            raw_status = "paid"

        if payment_id is None and not provider_payment_id:
            raise PaymentProviderError("Payment identifier is missing")

        return PaymentWebhookEvent(
            provider=self.provider_name,
            status=self._status_from_raw(raw_status),
            payment_id=payment_id,
            provider_payment_id=str(provider_payment_id) if provider_payment_id else None,
            provider_transaction_id=str(provider_transaction_id) if provider_transaction_id else None,
            amount=self._coerce_float(payload.get("amount")),
            currency=str(payload.get("currency")) if payload.get("currency") else None,
            raw_payload=self._dump_payload(payload, raw_payload),
        )
