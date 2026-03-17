from fastapi import APIRouter, Request

from backend.api.routes._webhook_utils import handle_payment_webhook
from backend.integrations.payments.click import ClickPaymentProvider

router = APIRouter()


@router.post("/")
async def click_webhook(request: Request) -> dict:
    return await handle_payment_webhook(request, ClickPaymentProvider())
