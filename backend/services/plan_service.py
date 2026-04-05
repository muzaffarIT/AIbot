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
                "name": "⚡ Light",
                "description": "150 кредитов для старта",
                "price": 105000,
                "currency": "UZS",
                "credits_amount": 150,
                "duration_days": None,
            },
            {
                "code": "pro",
                "name": "💎 Standard",
                "description": "400 кредитов. Самый популярный",
                "price": 290000,
                "currency": "UZS",
                "credits_amount": 400,
                "duration_days": None,
            },
            {
                "code": "creator",
                "name": "🚀 Pro",
                "description": "800 кредитов для контент-мейкеров",
                "price": 580000,
                "currency": "UZS",
                "credits_amount": 800,
                "duration_days": None,
            },
            {
                "code": "ultra",
                "name": "👑 Ultra",
                "description": "2000 кредитов. Максимум возможностей",
                "price": 1390000,
                "currency": "UZS",
                "credits_amount": 2000,
                "duration_days": None,
            },
        ]

        for item in default_plans:
            existing = self.repo.get_by_code(item["code"])
            if existing:
                # Update price, credits and name if changed
                existing.price = item["price"]
                existing.currency = item["currency"]
                existing.credits_amount = item["credits_amount"]
                existing.name = item["name"]
                existing.description = item["description"]
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
