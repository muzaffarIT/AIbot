from sqlalchemy.orm import Session

from backend.db.repositories.plans import PlanRepository
from backend.models.plan import Plan


class PlanService:
    def __init__(self, db: Session) -> None:
        self.repo = PlanRepository(db)

    def get_plan_by_code(self, code: str) -> Plan | None:
        return self.repo.get_by_code(code)

    def get_active_plans(self) -> list[Plan]:
        return self.repo.get_active_plans()

    def seed_default_plans(self) -> None:
        default_plans = [
            {
                "code": "start",
                "name": "Start",
                "description": "100 кредитов для старта",
                "price": 7.5,
                "currency": "USD",
                "credits_amount": 100,
                "duration_days": 30,
            },
            {
                "code": "pro",
                "name": "Pro",
                "description": "300 кредитов для активного использования",
                "price": 19.0,
                "currency": "USD",
                "credits_amount": 300,
                "duration_days": 30,
            },
            {
                "code": "max",
                "name": "Max",
                "description": "1000 кредитов для интенсивной работы",
                "price": 49.0,
                "currency": "USD",
                "credits_amount": 1000,
                "duration_days": 30,
            },
        ]

        for item in default_plans:
            existing = self.repo.get_by_code(item["code"])
            if existing:
                continue

            self.repo.create_plan(
                code=item["code"],
                name=item["name"],
                description=item["description"],
                price=item["price"],
                currency=item["currency"],
                credits_amount=item["credits_amount"],
                duration_days=item["duration_days"],
                is_active=True,
            )
