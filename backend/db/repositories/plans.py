from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.plan import Plan


class PlanRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, plan_id: int) -> Plan | None:
        stmt = select(Plan).where(Plan.id == plan_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_code(self, code: str) -> Plan | None:
        stmt = select(Plan).where(Plan.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active_plans(self) -> list[Plan]:
        stmt = (
            select(Plan)
            .where(Plan.is_active.is_(True))
            .order_by(Plan.price.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create_plan(
        self,
        code: str,
        name: str,
        description: str | None,
        price: float,
        currency: str,
        credits_amount: int,
        duration_days: int | None,
        is_active: bool = True,
    ) -> Plan:
        plan = Plan(
            code=code,
            name=name,
            description=description,
            price=price,
            currency=currency,
            credits_amount=credits_amount,
            duration_days=duration_days,
            is_active=is_active,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan