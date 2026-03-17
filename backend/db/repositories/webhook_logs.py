from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models.webhook_log import WebhookLog


class WebhookLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_log(
        self,
        provider: str,
        event_type: str,
        status: str,
        request_headers: str | None,
        payload: str | None,
        http_status: int | None = None,
        payment_id: int | None = None,
        provider_payment_id: str | None = None,
        error_message: str | None = None,
    ) -> WebhookLog:
        log = WebhookLog(
            provider=provider,
            event_type=event_type,
            status=status,
            http_status=http_status,
            payment_id=payment_id,
            provider_payment_id=provider_payment_id,
            request_headers=request_headers,
            payload=payload,
            error_message=error_message,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def update_log(
        self,
        log: WebhookLog,
        *,
        status: str | None = None,
        http_status: int | None = None,
        payment_id: int | None = None,
        provider_payment_id: str | None = None,
        error_message: str | None = None,
    ) -> WebhookLog:
        if status is not None:
            log.status = status
        if http_status is not None:
            log.http_status = http_status
        if payment_id is not None:
            log.payment_id = payment_id
        if provider_payment_id is not None:
            log.provider_payment_id = provider_payment_id
        if error_message is not None:
            log.error_message = error_message
        log.processed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(log)
        return log
