from enum import StrEnum


class PaymentStatus(StrEnum):
    CREATED = "created"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"