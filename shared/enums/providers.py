from enum import StrEnum


class AIProvider(StrEnum):
    NANO_BANANA = "nano_banana"
    KLING = "kling"
    VEO = "veo"


class PaymentProvider(StrEnum):
    CARDS = "cards"
    PAYME = "payme"
    CLICK = "click"
