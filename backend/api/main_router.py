from fastapi import APIRouter

from backend.api.routes.users import router as users_router
from backend.api.routes.balances import router as balances_router
from backend.api.routes.plans import router as plans_router
from backend.api.routes.orders import router as orders_router
from backend.api.routes.payments import router as payments_router
from backend.api.routes.jobs import router as jobs_router
from backend.api.routes.cards_webhook import router as cards_webhook_router
from backend.api.routes.payme_webhook import router as payme_webhook_router
from backend.api.routes.click_webhook import router as click_webhook_router

api_router = APIRouter()
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(balances_router, prefix="/balances", tags=["balances"])
api_router.include_router(plans_router, prefix="/plans", tags=["plans"])
api_router.include_router(orders_router, prefix="/orders", tags=["orders"])
api_router.include_router(payments_router, prefix="/payments", tags=["payments"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
api_router.include_router(cards_webhook_router, prefix="/webhooks/cards", tags=["webhooks"])
api_router.include_router(payme_webhook_router, prefix="/webhooks/payme", tags=["webhooks"])
api_router.include_router(click_webhook_router, prefix="/webhooks/click", tags=["webhooks"])
