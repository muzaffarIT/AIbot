from enum import StrEnum


class AIProvider(StrEnum):
    NANO_BANANA = "nano_banana"
    KLING = "kling"
    VEO = "veo"
    GPT_IMAGE = "gpt_image"


class PaymentProvider(StrEnum):
    CARDS = "cards"
    PAYME = "payme"
    CLICK = "click"
