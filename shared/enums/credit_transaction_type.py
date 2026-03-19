from enum import StrEnum


class CreditTransactionType(StrEnum):
    TOPUP = "topup"
    RESERVE = "reserve"
    WRITEOFF = "writeoff"
    REFUND = "refund"
    BONUS = "bonus"