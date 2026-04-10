from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService

router = APIRouter()


def serialize_transaction(transaction) -> dict:
    return {
        "id": transaction.id,
        "transaction_type": transaction.transaction_type,
        "amount": transaction.amount,
        "balance_before": transaction.balance_before,
        "balance_after": transaction.balance_after,
        "reference_type": transaction.reference_type,
        "reference_id": transaction.reference_id,
        "comment": transaction.comment,
        "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
    }


@router.get("/telegram/{telegram_user_id}/transactions")
def get_balance_transactions_by_telegram_user_id(
    telegram_user_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
) -> dict:
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        user = user_service.get_user_by_telegram_id(telegram_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        balance = balance_service.get_balance_value(user.id)
        transactions = balance_service.get_last_transactions(user.id, limit=limit)

        return {
            "user_id": user.id,
            "telegram_user_id": user.telegram_user_id,
            "credits_balance": balance,
            "transactions": [serialize_transaction(item) for item in transactions],
        }
    finally:
        db.close()


@router.get("/telegram/{telegram_user_id}/uzs-transactions")
def get_uzs_transactions(
    telegram_user_id: int,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(telegram_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        from sqlalchemy import text
        rows = db.execute(text(
            "SELECT id, amount, type, comment, balance_after, created_at "
            "FROM uzs_transactions WHERE user_id = :uid "
            "ORDER BY created_at DESC LIMIT :lim"
        ), {"uid": user.id, "lim": limit}).fetchall()

        return {
            "user_id": user.id,
            "telegram_user_id": user.telegram_user_id,
            "uzs_balance": getattr(user, "uzs_balance", 0) or 0,
            "transactions": [
                {
                    "id": r.id,
                    "amount": r.amount,
                    "type": r.type,
                    "comment": r.comment,
                    "balance_after": r.balance_after,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
        }
    finally:
        db.close()


@router.get("/telegram/{telegram_user_id}")
def get_balance_by_telegram_user_id(telegram_user_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        user = user_service.get_user_by_telegram_id(telegram_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        balance = balance_service.get_balance_value(user.id)

        return {
            "user_id": user.id,
            "telegram_user_id": user.telegram_user_id,
            "credits_balance": balance,
        }
    finally:
        db.close()
