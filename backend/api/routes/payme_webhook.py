from fastapi import APIRouter, Request

from backend.api.routes._webhook_utils import handle_payment_webhook
from backend.integrations.payments.payme import PaymePaymentProvider

router = APIRouter()


@router.post("/")
async def payme_webhook(request: Request) -> dict:
    return await handle_payment_webhook(request, PaymePaymentProvider())
