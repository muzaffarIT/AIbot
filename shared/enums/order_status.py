from enum import StrEnum


class OrderStatus(StrEnum):
    PENDING = "pending"
    WAITING_PAYMENT = "waiting_payment"
    PAID = "paid"
    CANCELLED = "cancelled"
    FAILED = "failed"
    EXPIRED = "expired"