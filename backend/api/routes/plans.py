from fastapi import APIRouter
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.services.plan_service import PlanService

router = APIRouter()


@router.get("")
@router.get("/")
def get_active_plans() -> list[dict]:
    db: Session = SessionLocal()
    try:
        plan_service = PlanService(db)
        plans = plan_service.get_active_plans()

        return [
            {
                "id": plan.id,
                "code": plan.code,
                "name": plan.name,
                "description": plan.description,
                "price": plan.price,
                "currency": plan.currency,
                "credits_amount": plan.credits_amount,
                "duration_days": plan.duration_days,
                "is_active": plan.is_active,
            }
            for plan in plans
        ]
    finally:
        db.close()
