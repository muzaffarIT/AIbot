from sqlalchemy.orm import Session

from backend.db.repositories.balances import BalanceRepository
from backend.db.repositories.credit_transactions import CreditTransactionRepository
from backend.models.balance import Balance
from shared.enums.credit_transaction_type import CreditTransactionType

UZS_PER_CREDIT = 700  # How many sums per 1 credit (auto-conversion rate)


class BalanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
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

    def get_uzs_balance(self, user_id: int) -> int:
        from backend.models.user import User
        user = self.db.query(User).filter(User.id == user_id).first()
        return getattr(user, "uzs_balance", 0) or 0 if user else 0

    def add_uzs(self, user_id: int, amount: int) -> int:
        """Add sums to user's UZS wallet. Returns new balance."""
        from backend.models.user import User
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            user.uzs_balance = (getattr(user, "uzs_balance", 0) or 0) + amount
            self.db.commit()
            return user.uzs_balance
        return 0

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

        # Auto-convert from UZS balance if credits are insufficient
        if balance.credits_balance < amount:
            deficit = amount - balance.credits_balance
            uzs_needed = deficit * UZS_PER_CREDIT
            from backend.models.user import User
            user = self.db.query(User).filter(User.id == user_id).first()
            uzs_bal = (getattr(user, "uzs_balance", 0) or 0) if user else 0
            if user and uzs_bal >= uzs_needed:
                user.uzs_balance = uzs_bal - uzs_needed
                self.db.flush()
                # Add the missing credits from UZS
                self.add_credits(
                    user_id, deficit,
                    transaction_type=CreditTransactionType.TOPUP,
                    comment=f"Авто-конвертация: {uzs_needed:,} so'm → {deficit} kr.".replace(",", " "),
                )
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
