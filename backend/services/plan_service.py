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
                "name": "⚡ Start",
                "description": "100 кредитов для старта",
                "price": 59000,
                "currency": "UZS",
                "credits_amount": 100,
                "duration_days": None,
            },
            {
                "code": "pro",
                "name": "💎 Pro",
                "description": "300 кредитов для активного использования",
                "price": 149000,
                "currency": "UZS",
                "credits_amount": 300,
                "duration_days": None,
            },
            {
                "code": "creator",
                "name": "🚀 Creator",
                "description": "600 кредитов для создателей контента",
                "price": 269000,
                "currency": "UZS",
                "credits_amount": 600,
                "duration_days": None,
            },
            {
                "code": "ultra",
                "name": "👑 Ultra",
                "description": "1500 кредитов для профессионалов",
                "price": 590000,
                "currency": "UZS",
                "credits_amount": 1500,
                "duration_days": None,
            },
        ]

        for item in default_plans:
            existing = self.repo.get_by_code(item["code"])
            if existing:
                # Update price/currency if changed
                if existing.price != item["price"] or existing.currency != item["currency"]:
                    existing.price = item["price"]
                    existing.currency = item["currency"]
                    self.repo.db.commit()
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
