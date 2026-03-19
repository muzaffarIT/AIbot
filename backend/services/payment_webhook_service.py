from sqlalchemy.orm import Session

from backend.integrations.payments.base import (
    BasePaymentProvider,
    PaymentProviderAuthError,
    PaymentProviderError,
)
from backend.services.payment_service import PaymentService
from backend.services.webhook_log_service import WebhookLogService


class PaymentWebhookService:
    def __init__(self, db: Session) -> None:
        self.payment_service = PaymentService(db)
        self.webhook_logs = WebhookLogService(db)

    def handle_callback(
        self,
        *,
        provider: BasePaymentProvider,
        payload: dict,
        auth_headers: dict[str, str],
        logged_headers: dict[str, str],
        raw_payload: str,
    ):
        log = self.webhook_logs.create_received_log(
            provider=provider.provider_name,
            headers=logged_headers,
            payload=raw_payload,
        )

        try:
            event = provider.parse_webhook(payload, auth_headers, raw_payload)
            payment = self.payment_service.process_webhook_event(event)
            self.webhook_logs.mark_processed(
                log,
                status="processed",
                http_status=200,
                payment_id=payment.id,
                provider_payment_id=payment.provider_payment_id,
            )
            return payment
        except PaymentProviderAuthError as exc:
            self.webhook_logs.mark_processed(
                log,
                status="rejected",
                http_status=401,
                error_message=str(exc),
            )
            raise
        except PaymentProviderError as exc:
            self.webhook_logs.mark_processed(
                log,
                status="invalid",
                http_status=400,
                error_message=str(exc),
            )
            raise
        except ValueError as exc:
            self.webhook_logs.mark_processed(
                log,
                status="failed",
                http_status=404,
                error_message=str(exc),
            )
            raise
