from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.credit_transaction import CreditTransaction


class CreditTransactionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_transaction(
        self,
        user_id: int,
        transaction_type: str,
        amount: int,
        balance_before: int,
        balance_after: int,
        reference_type: str | None = None,
        reference_id: str | None = None,
        comment: str | None = None,
    ) -> CreditTransaction:
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_type=reference_type,
            reference_id=reference_id,
            comment=comment,
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_last_transactions(self, user_id: int, limit: int = 10) -> list[CreditTransaction]:
        stmt = (
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user_id)
            .order_by(CreditTransaction.id.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())