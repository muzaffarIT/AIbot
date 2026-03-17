import json

from sqlalchemy.orm import Session

from backend.db.repositories.webhook_logs import WebhookLogRepository
from backend.models.webhook_log import WebhookLog


class WebhookLogService:
    def __init__(self, db: Session) -> None:
        self.repo = WebhookLogRepository(db)

    def create_received_log(
        self,
        provider: str,
        headers: dict[str, str],
        payload: str,
    ) -> WebhookLog:
        return self.repo.create_log(
            provider=provider,
            event_type="payment_callback",
            status="received",
            request_headers=json.dumps(headers, ensure_ascii=True, sort_keys=True),
            payload=payload,
        )

    def mark_processed(
        self,
        log: WebhookLog,
        *,
        status: str,
        http_status: int,
        payment_id: int | None = None,
        provider_payment_id: str | None = None,
        error_message: str | None = None,
    ) -> WebhookLog:
        return self.repo.update_log(
            log,
            status=status,
            http_status=http_status,
            payment_id=payment_id,
            provider_payment_id=provider_payment_id,
            error_message=error_message,
        )
