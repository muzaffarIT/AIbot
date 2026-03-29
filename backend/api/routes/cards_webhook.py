from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from backend.api.deps import get_db

from backend.api.routes._webhook_utils import handle_payment_webhook
from backend.integrations.payments.cards import CardsPaymentProvider

router = APIRouter()


@router.post("/")
async def cards_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    return await handle_payment_webhook(request, CardsPaymentProvider(), db)
