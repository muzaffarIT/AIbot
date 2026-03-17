from backend.db.base import Base
from backend.db.session import engine
from backend.db.session import SessionLocal
from backend import models  # noqa: F401
from backend.services.plan_service import PlanService


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        PlanService(db).seed_default_plans()
    finally:
        db.close()
