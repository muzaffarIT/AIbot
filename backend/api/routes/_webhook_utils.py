import json

from fastapi import HTTPException, Request

from backend.integrations.payments.base import (
    BasePaymentProvider,
    PaymentProviderAuthError,
    PaymentProviderError,
    sanitize_headers,
)
from backend.services.payment_webhook_service import PaymentWebhookService
from sqlalchemy.orm import Session

async def parse_request_payload(request: Request) -> tuple[dict, str]:
    raw_bytes = await request.body()
    raw_text = raw_bytes.decode("utf-8") if raw_bytes else ""
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type and raw_text:
        try:
            return json.loads(raw_text), raw_text
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        payload = {key: value for key, value in form.items()}
        return payload, json.dumps(payload, ensure_ascii=True, sort_keys=True)

    if raw_text:
        try:
            return json.loads(raw_text), raw_text
        except json.JSONDecodeError:
            return {"raw": raw_text}, raw_text

    return {}, "{}"


async def handle_payment_webhook(
    request: Request,
    provider: BasePaymentProvider,
    db: Session,
) -> dict:
    payload, raw_text = await parse_request_payload(request)
    auth_headers = dict(request.headers)
    logged_headers = sanitize_headers(auth_headers)

    try:
        service = PaymentWebhookService(db)
        payment = service.handle_callback(
            provider=provider,
            payload=payload,
            auth_headers=auth_headers,
            logged_headers=logged_headers,
            raw_payload=raw_text,
        )
        return {
            "status": "accepted",
            "payment_id": payment.id,
            "payment_status": payment.status,
            "provider_payment_id": payment.provider_payment_id,
        }
    except PaymentProviderAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    except PaymentProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
