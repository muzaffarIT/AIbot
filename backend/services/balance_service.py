from sqlalchemy.orm import Session

from backend.db.repositories.balances import BalanceRepository
from backend.db.repositories.credit_transactions import CreditTransactionRepository
from backend.models.balance import Balance
from shared.enums.credit_transaction_type import CreditTransactionType


class BalanceService:
    def __init__(self, db: Session) -> None:
        self.repo = BalanceRepository(db)
        self.tx_repo = CreditTransactionRepository(db)

    def get_or_create_balance(self, user_id: int) -> Balance:
        balance = self.repo.get_by_user_id(user_id)
        if balance:
            return balance

        return self.repo.create_balance(user_id=user_id, credits_balance=0)

    def get_balance_value(self, user_id: int) -> int:
        balance = self.repo.get_by_user_id(user_id)
        if not balance:
            balance = self.repo.create_balance(user_id=user_id, credits_balance=0)
        return balance.credits_balance

    def add_credits(
        self,
        user_id: int,
        amount: int,
        transaction_type: str = CreditTransactionType.TOPUP,
        reference_type: str | None = None,
        reference_id: str | None = None,
        comment: str | None = None,
    ) -> int:
        balance = self.get_or_create_balance(user_id)
        before = balance.credits_balance
        updated = self.repo.add_credits(balance, amount)
        after = updated.credits_balance

        self.tx_repo.create_transaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=before,
            balance_after=after,
            reference_type=reference_type,
            reference_id=reference_id,
            comment=comment,
        )
        return after

    def subtract_credits(
        self,
        user_id: int,
        amount: int,
        transaction_type: str = CreditTransactionType.WRITEOFF,
        reference_type: str | None = None,
        reference_id: str | None = None,
        comment: str | None = None,
    ) -> int:
        balance = self.get_or_create_balance(user_id)
        before = balance.credits_balance
        updated = self.repo.subtract_credits(balance, amount)
        after = updated.credits_balance

        self.tx_repo.create_transaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=-amount,
            balance_before=before,
            balance_after=after,
            reference_type=reference_type,
            reference_id=reference_id,
            comment=comment,
        )
        return after

    def get_last_transactions(self, user_id: int, limit: int = 10):
        return self.tx_repo.get_last_transactions(user_id=user_id, limit=limit)