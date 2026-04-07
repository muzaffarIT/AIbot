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
        "referral_earnings": getattr(user, "referral_earnings", 0) or 0,
        "uzs_balance": getattr(user, "uzs_balance", 0) or 0,
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

            # Award any earned-but-unclaimed achievements silently on sync
            try:
                from bot.services.achievements import check_and_award_achievements
                import logging as _logging
                check_and_award_achievements(
                    db=db,
                    user_id=user.id,
                    telegram_id=user.telegram_user_id,
                    lang=user.language_code or "ru",
                )
                db.commit()
            except Exception as _ach_err:
                _logging.getLogger(__name__).warning(f"Achievement check failed on sync: {_ach_err}")

            credits_balance = balance_service.get_balance_value(user.id)
            referral_count = get_referral_count(db, user.telegram_user_id)
            return serialize_user(user, credits_balance, referral_count)
        except Exception as e:
            # Fallback for sync to never crash frontend
            # NOTE: do NOT return language_code here — it would overwrite user's chosen language
            return {
                "telegram_user_id": payload.telegram_id,
                "credits_balance": 0,
                "language_code": None,
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

        # Proactively check and award any newly earned achievements
        try:
            from bot.services.achievements import check_and_award_achievements
            newly = check_and_award_achievements(
                db=db,
                user_id=user.id,
                telegram_id=user.telegram_user_id,
                lang=user.language_code or "ru",
            )
            if newly:
                db.commit()
        except Exception:
            pass

        lang = getattr(user, "language_code", "ru") or "ru"
        ALL = [
            {"code":"first_gen", "name_ru":"Первый шаг",    "name_uz":"Birinchi qadam", "emoji":"🌱","bonus":2},
            {"code":"artist_10", "name_ru":"Художник",       "name_uz":"Rassom",         "emoji":"🎨","bonus":5},
            {"code":"director",  "name_ru":"Режиссёр",       "name_uz":"Rejissyor",      "emoji":"🎬","bonus":5},
            {"code":"buyer",     "name_ru":"Меценат",        "name_uz":"Homiy",          "emoji":"💎","bonus":10},
            {"code":"streak_7",  "name_ru":"Огонь",          "name_uz":"Olov",           "emoji":"🔥","bonus":15},
            {"code":"referrer",  "name_ru":"Амбассадор",     "name_uz":"Ambassador",     "emoji":"👥","bonus":25},
            {"code":"centurion", "name_ru":"Сотня",          "name_uz":"Yuz",            "emoji":"💯","bonus":30},
            {"code":"legend",    "name_ru":"Легенда",        "name_uz":"Afsona",         "emoji":"👑","bonus":100},
        ]
        try:
            earned_rows = db.query(Achievement).filter(Achievement.user_id == user.id).all()
            earned = {a.achievement_code for a in earned_rows}
        except Exception:
            earned = set()
        result = []
        for a in ALL:
            name = a["name_uz"] if lang == "uz" else a["name_ru"]
            result.append({
                "code": a["code"],
                "name": name,
                "name_ru": a["name_ru"],
                "name_uz": a["name_uz"],
                "emoji": a["emoji"],
                "bonus": a["bonus"],
                "earned": a["code"] in earned,
            })
        return result
    finally:
        db.close()


@router.patch("/language")
def update_language(payload: LanguageUpdateRequest, db: Session = Depends(get_db)) -> dict:
    """Update user's language preference."""
    try:
        user_service = UserService(db)
        lang = payload.language if payload.language in ("ru", "uz") else "ru"
        user_service.set_user_language(payload.telegram_user_id, lang)
        return {"success": True, "language": lang}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
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
