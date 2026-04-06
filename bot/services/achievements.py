"""
Achievement definitions and checking logic.
Called after each generation completion and successful purchase.
"""
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Achievement definitions
@dataclass
class AchievementDef:
    code: str
    emoji: str
    name_ru: str
    name_uz: str
    bonus_credits: int
    description_ru: str
    description_uz: str


ACHIEVEMENTS: list[AchievementDef] = [
    AchievementDef("first_gen",  "🌱", "Первый шаг",   "Birinchi qadam", 2,  "Первая генерация",     "Birinchi generatsiya"),
    AchievementDef("artist_10",  "🎨", "Художник",      "Rassom",         5,  "10 картинок",          "10 ta rasm"),
    AchievementDef("director",   "🎬", "Режиссёр",      "Rejissyor",      5,  "Первое видео",         "Birinchi video"),
    AchievementDef("buyer",      "💎", "Меценат",       "Homiy",          10, "Первая покупка",        "Birinchi xarid"),
    AchievementDef("streak_7",   "🔥", "Огонь",         "Olov",           15, "7 дней стрик",         "7 kun streak"),
    AchievementDef("centurion",  "💯", "Сотня",         "Yuz",            30, "100 генераций",        "100 ta generatsiya"),
    AchievementDef("referrer",   "👥", "Амбассадор",    "Ambassador",     25, "5 рефералов",          "5 ta referal"),
    AchievementDef("legend",     "👑", "Легенда",       "Afsona",         100,"500 генераций",        "500 ta generatsiya"),
]

ACHIEVEMENT_MAP = {a.code: a for a in ACHIEVEMENTS}


def check_and_award_achievements(
    db,
    user_id: int,
    telegram_id: int,
    lang: str = "ru",
) -> list[tuple[AchievementDef, int]]:
    """
    Check which achievements the user should receive.
    Returns list of (achievement, bonus_credits) for newly awarded.
    Must be called inside a DB session — does NOT commit, caller should commit.
    """
    from backend.models.achievement import Achievement
    from backend.models.generation_job import GenerationJob
    from shared.enums.job_status import JobStatus
    from shared.enums.providers import AIProvider

    # Already earned codes
    earned_codes = {
        a.achievement_code
        for a in db.query(Achievement).filter(Achievement.user_id == user_id).all()
    }

    # Stats for user — use legacy db.query() style for reliable count
    completed_jobs = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.user_id == user_id,
            GenerationJob.status == JobStatus.COMPLETED,
        )
        .count()
    )

    image_jobs = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.user_id == user_id,
            GenerationJob.status == JobStatus.COMPLETED,
            GenerationJob.provider == AIProvider.NANO_BANANA,
        )
        .count()
    )

    video_jobs = (
        db.query(GenerationJob)
        .filter(
            GenerationJob.user_id == user_id,
            GenerationJob.status == JobStatus.COMPLETED,
            GenerationJob.provider.in_([AIProvider.VEO, AIProvider.KLING]),
        )
        .count()
    )

    from backend.models.credit_transaction import CreditTransaction
    purchase_count = (
        db.query(CreditTransaction)
        .filter(
            CreditTransaction.user_id == user_id,
            CreditTransaction.reference_type == "payment",
        )
        .count()
    )

    from backend.models.user import User
    user = db.get(User, user_id)
    streak = getattr(user, "daily_streak", 0) or 0

    from backend.db.repositories.users import UserRepository
    referral_count = UserRepository(db).get_referral_count(user_id)

    def should_award(code: str) -> bool:
        if code in earned_codes:
            return False
        if code == "first_gen":   return completed_jobs >= 1
        if code == "artist_10":   return image_jobs >= 10
        if code == "director":    return video_jobs >= 1
        if code == "buyer":       return purchase_count >= 1
        if code == "streak_7":    return streak >= 7
        if code == "centurion":   return completed_jobs >= 100
        if code == "referrer":    return referral_count >= 5
        if code == "legend":      return completed_jobs >= 500
        return False

    from backend.services.balance_service import BalanceService
    balance_service = BalanceService(db)

    newly_awarded: list[tuple[AchievementDef, int]] = []
    for ach in ACHIEVEMENTS:
        if should_award(ach.code):
            db.add(Achievement(user_id=user_id, achievement_code=ach.code))
            balance_service.add_credits(user_id, ach.bonus_credits, f"achievement_{ach.code}")
            newly_awarded.append((ach, ach.bonus_credits))
            logger.info(f"[Achievement] user={telegram_id} earned {ach.code} (+{ach.bonus_credits} credits)")

    return newly_awarded
