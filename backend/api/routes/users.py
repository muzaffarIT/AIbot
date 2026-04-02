from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.services.user_service import UserService
from backend.services.balance_service import BalanceService
from backend.models.user import User
from backend.api.deps import verify_tma_auth, get_db

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


class LanguageUpdateRequest(BaseModel):
    telegram_user_id: int
    language: str


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
        "daily_streak": getattr(user, "daily_streak", 0) or 0,
        "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
    }

def get_referral_count(db: Session, telegram_id: int) -> int:
    return db.query(User).filter(User.referred_by_telegram_id == telegram_id).count()


@router.post("/sync")
def sync_user(payload: SyncUserRequest, token_user: dict = Depends(verify_tma_auth), db: Session = Depends(get_db)) -> dict:
    if str(payload.telegram_id) != str(token_user.get("id")):
        raise HTTPException(status_code=403, detail="Telegram ID mismatch")
    """Upsert user from Mini App. Always returns 200 with user data."""
    try:
        user_service = UserService(db)
        balance_service = BalanceService(db)

        try:
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
        except Exception as e:
            # Fallback for sync to never crash frontend
            return {
                "telegram_user_id": payload.telegram_id,
                "credits_balance": 0,
                "language_code": payload.language_code or "ru",
                "id": 0,
                "username": payload.username,
                "first_name": payload.first_name,
                "last_name": payload.last_name,
                "referral_count": 0
            }
    finally:
        db.close()


@router.post("/ensure")
def ensure_user(payload: EnsureUserRequest, token_user: dict = Depends(verify_tma_auth), db: Session = Depends(get_db)) -> dict:
    if str(payload.telegram_user_id) != str(token_user.get("id")):
        raise HTTPException(status_code=403, detail="Telegram ID mismatch")
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
def get_user(telegram_user_id: int, db: Session = Depends(get_db)) -> dict:
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


@router.get("/{telegram_id}/achievements")
async def get_achievements(telegram_id: int, db: Session = Depends(get_db)):
    from backend.models.achievement import Achievement
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(telegram_id)
        if not user:
            return []
        ALL = [
            {"code":"first_gen","name":"Первая генерация","emoji":"🌱","bonus":2},
            {"code":"artist_10","name":"10 картинок","emoji":"🎨","bonus":5},
            {"code":"director","name":"Первое видео","emoji":"🎬","bonus":5},
            {"code":"buyer","name":"Первая покупка","emoji":"💎","bonus":10},
            {"code":"streak_7","name":"Стрик 7 дней","emoji":"🔥","bonus":15},
            {"code":"referrer_5","name":"5 рефералов","emoji":"👥","bonus":25},
            {"code":"centurion","name":"100 генераций","emoji":"💯","bonus":30},
            {"code":"legend","name":"500 генераций","emoji":"👑","bonus":100},
        ]
        try:
            earned = {a.code for a in db.query(Achievement).filter(
                Achievement.user_id == user.id).all()}
        except Exception:
            earned = set()
        return [{**a, "earned": a["code"] in earned} for a in ALL]
    finally:
        db.close()


@router.get("/{telegram_id}/referral")
async def get_referral(telegram_id: int, db: Session = Depends(get_db)):
    try:
        user_service = UserService(db)
        user = user_service.get_user_by_telegram_id(telegram_id)
        if not user:
            return {"referral_code":"","referral_count":0, "referral_earnings":0}
        return {
            "referral_code": user.referral_code or "",
            "referral_count": get_referral_count(db, user.telegram_user_id),
            "referral_earnings": user.referral_earnings or 0
        }
    finally:
        db.close()
