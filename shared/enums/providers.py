from enum import StrEnum


class AIProvider(StrEnum):
    NANO_BANANA = "nano_banana"
    KLING = "kling"
    VEO = "veo"
    GPT_IMAGE = "gpt_image"
    # Generic KIE "market" image model — the exact slug travels in
    # job_payload["_kie_model"], so new KIE image models can be added by
    # registering a tier in media_tiers.py without touching the worker.
    KIE_IMAGE = "kie_image"


class PaymentProvider(StrEnum):
    CARDS = "cards"
    PAYME = "payme"
    CLICK = "click"
