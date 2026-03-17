from backend.db.base import Base
from backend.db.session import engine, SessionLocal
from backend.models import User, Balance, CreditTransaction, Plan, Order, Payment
from backend.services.plan_service import PlanService


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        plan_service = PlanService(db)
        plan_service.seed_default_plans()
    finally:
        db.close()