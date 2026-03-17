import json
from abc import ABC, abstractmethod
from typing import Any, Mapping

from backend.core.security import extract_bearer_token, is_secret_valid
from shared.dto.payment_payloads import PaymentWebhookEvent
from shared.enums.payment_status import PaymentStatus


class PaymentProviderError(ValueError):
    pass


class PaymentProviderAuthError(PermissionError):
    pass


def sanitize_headers(headers: Mapping[str, str]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in headers.items():
        lowered = key.lower()
        if "authorization" in lowered or "secret" in lowered or "signature" in lowered:
            sanitized[key] = "<redacted>"
        else:
            sanitized[key] = value
    return sanitized


class BasePaymentProvider(ABC):
    provider_name: str
    secret_key: str | None = None
    secret_headers: tuple[str, ...] = ("x-webhook-secret",)

    def __init__(self, secret_key: str | None = None) -> None:
        if secret_key is not None:
            self.secret_key = secret_key

    def parse_webhook(
        self,
        payload: dict[str, Any],
        headers: Mapping[str, str],
        raw_payload: str,
    ) -> PaymentWebhookEvent:
        self._verify_secret(headers)
        return self._build_event(payload, raw_payload)

    def _verify_secret(self, headers: Mapping[str, str]) -> None:
        if not self.secret_key:
            return

        bearer_token = extract_bearer_token(headers.get("authorization"))
        candidates = [bearer_token] if bearer_token else []
        candidates.extend(headers.get(name) for name in self.secret_headers)

        if any(is_secret_valid(self.secret_key, candidate) for candidate in candidates):
            return

        raise PaymentProviderAuthError("Invalid webhook secret")

    def _coerce_int(self, value: Any) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    def _coerce_float(self, value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(str(value))
        except (TypeError, ValueError):
            return None

    def _status_from_raw(self, value: Any) -> str:
        normalized = str(value).strip().lower()

        if normalized in {"paid", "success", "completed", "complete"}:
            return PaymentStatus.PAID
        if normalized in {"processing", "pending", "in_progress"}:
            return PaymentStatus.PROCESSING
        if normalized in {"created", "new"}:
            return PaymentStatus.CREATED
        if normalized in {"failed", "error"}:
            return PaymentStatus.FAILED
        if normalized in {"cancelled", "canceled"}:
            return PaymentStatus.CANCELLED
        if normalized in {"refunded"}:
            return PaymentStatus.REFUNDED

        if normalized in {"2"}:
            return PaymentStatus.PAID
        if normalized in {"1"}:
            return PaymentStatus.PROCESSING
        if normalized in {"0"}:
            return PaymentStatus.CREATED
        if normalized.startswith("-"):
            return PaymentStatus.CANCELLED

        raise PaymentProviderError("Unsupported payment status")

    def _dump_payload(self, payload: dict[str, Any], raw_payload: str) -> str:
        if raw_payload:
            return raw_payload
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)

    @abstractmethod
    def _build_event(
        self,
        payload: dict[str, Any],
        raw_payload: str,
    ) -> PaymentWebhookEvent:
        raise NotImplementedError
