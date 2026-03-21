from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from backend.models.user import User

router = APIRouter()

FREE_CREDITS_ON_REGISTER = 5


class EnsureUserRequest(BaseModel):
    telegram_user_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None


class SyncUserRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    language_code: str | None = None


def serialize_user(user, credits_balance: int, referral_count: int = 0) -> dict:
    return {
        "id": user.id,
        "telegram_user_id": user.telegram_user_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code,
        "credits_balance": credits_balance,
        "referral_count": referral_count,
    }

def get_referral_count(db: Session, telegram_id: int) -> int:
    return db.query(User).filter(User.referred_by_telegram_id == telegram_id).count()


@router.post("/sync")
def sync_user(payload: SyncUserRequest) -> dict:
    """Upsert user from Mini App. Always returns 200 with user data."""
    db: Session = SessionLocal()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        user = user_service.get_or_create_user(
            telegram_user_id=payload.telegram_id,
            username=payload.username,
            first_name=payload.first_name,
            last_name=payload.last_name,
            language_code=payload.language_code,
        )
        credits_balance = balance_service.get_balance_value(user.id)
        referral_count = get_referral_count(db, user.telegram_user_id)
        return serialize_user(user, credits_balance, referral_count)
    finally:
        db.close()


@router.post("/ensure")
def ensure_user(payload: EnsureUserRequest) -> dict:
    db: Session = SessionLocal()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        user = user_service.get_or_create_user(
            telegram_user_id=payload.telegram_user_id,
            username=payload.username,
            first_name=payload.first_name,
            last_name=payload.last_name,
            language_code=payload.language_code,
        )
        credits_balance = balance_service.get_balance_value(user.id)
        referral_count = get_referral_count(db, user.telegram_user_id)
        return serialize_user(user, credits_balance, referral_count)
    finally:
        db.close()


@router.get("/{telegram_user_id}")
def get_user(telegram_user_id: int) -> dict:
    db: Session = SessionLocal()
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)
        user = user_service.get_user_by_telegram_id(telegram_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        credits_balance = balance_service.get_balance_value(user.id)
        referral_count = get_referral_count(db, user.telegram_user_id)
        return serialize_user(user, credits_balance, referral_count)
    finally:
        db.close()
