from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.balance import Balance


class BalanceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_id(self, user_id: int) -> Balance | None:
        stmt = select(Balance).where(Balance.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def create_balance(self, user_id: int, credits_balance: int = 0) -> Balance:
        balance = Balance(
            user_id=user_id,
            credits_balance=credits_balance,
        )
        self.db.add(balance)
        self.db.commit()
        self.db.refresh(balance)
        return balance

    def set_balance(self, balance: Balance, credits_balance: int) -> Balance:
        balance.credits_balance = credits_balance
        self.db.commit()
        self.db.refresh(balance)
        return balance

    def add_credits(self, balance: Balance, amount: int) -> Balance:
        balance.credits_balance += amount
        self.db.commit()
        self.db.refresh(balance)
        return balance

    def subtract_credits(self, balance: Balance, amount: int) -> Balance:
        if balance.credits_balance < amount:
            raise ValueError("Not enough credits")
        balance.credits_balance -= amount
        self.db.commit()
        self.db.refresh(balance)
        return balance
