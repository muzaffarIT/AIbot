import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from backend.db.repositories.users import UserRepository
from backend.services.balance_service import BalanceService
from backend.models.user import User
from backend.core.config import settings

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, db: Session) -> None:
        self.repo = UserRepository(db)
        self.balance_service = BalanceService(db)

    def get_or_create_user(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None = None,
    ) -> User:
        user = self.repo.get_by_telegram_user_id(telegram_user_id)
        if user:
            user = self.repo.update_profile(
                user,
                username=username,
                first_name=first_name,
                last_name=last_name,
                # Preserve user's chosen language (set via bot); only set if not yet chosen
                language_code=language_code if not user.language_code else None,
            )
            self.balance_service.get_or_create_balance(user.id)
            return user

        user = self.repo.create_user(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code or settings.default_language,
        )
        self.balance_service.get_or_create_balance(user.id)
        return user

    def get_user_language(self, telegram_user_id: int) -> str:
        user = self.repo.get_by_telegram_user_id(telegram_user_id)
        if not user:
            return settings.default_language
        return user.language_code

    def set_user_language(self, telegram_user_id: int, language_code: str) -> str:
        user = self.repo.get_by_telegram_user_id(telegram_user_id)
        if not user:
            raise ValueError("User not found")
        updated_user = self.repo.update_language(user, language_code)
        return updated_user.language_code

    def get_user_by_telegram_id(self, telegram_user_id: int) -> User | None:
        return self.repo.get_by_telegram_user_id(telegram_user_id)

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.repo.get_by_id(user_id)

    def get_user_by_referral_code(self, code: str) -> User | None:
        return self.repo.get_by_referral_code(code)

    def set_referred_by(self, user_id: int, referrer_telegram_id: int) -> None:
        self.repo.set_referred_by(user_id, referrer_telegram_id)

    def get_referral_count(self, user_id: int) -> int:
        return self.repo.get_referral_count(user_id)

    def claim_daily_bonus(self, user_id: int) -> dict:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        # Use Tashkent calendar day so "once per day" matches the user's
        # lived day (the bot's audience is UZ). UTC would split a user's
        # day at 05:00 local and let them double-claim across it.
        from datetime import datetime, timezone, timedelta, date
        tashkent = timezone(timedelta(hours=5))
        now = datetime.now(tashkent)
        today = now.date()

        # ── Calendar-day guard: one bonus per local day ───────────────────
        if user.last_daily_claim is not None:
            # last_daily_claim may be tz-naive in old rows — make it comparable
            last = user.last_daily_claim
            if last.tzinfo is None:
                last = last.replace(tzinfo=tashkent)
            last_day = last.astimezone(tashkent).date()

            if last_day == today:
                # Already claimed today — show time remaining to the next day.
                tomorrow = today + timedelta(days=1)
                remaining = datetime.combine(tomorrow, datetime.min.time(), tzinfo=tashkent) - now
                hours_left = max(0, int(remaining.total_seconds() // 3600))
                minutes_left = max(0, int((remaining.total_seconds() % 3600) // 60))
                return {
                    "success": False,
                    "error": "already_claimed",
                    "hours": hours_left,
                    "minutes": minutes_left,
                    "streak": user.daily_streak,
                }

            # Streak bookkeeping (only when a new day actually started)
            gap_days = (today - last_day).days
            if gap_days == 1:
                user.daily_streak += 1
            else:
                # missed a day (or more) — reset the streak
                user.daily_streak = 1
        else:
            # First ever claim
            user.daily_streak = 1

        if user.daily_streak > user.max_streak:
            user.max_streak = user.daily_streak

        user.last_daily_claim = now

        # Bonus formula: grows with the streak 1→2→3...→10, then flat at 10.
        # Mirrors the UX users expect from daily-reward mechanics (games,
        # Suzma/Syntx-style retention) and matches the in-bot copy.
        bonus_credits = min(10, user.daily_streak)
        self.balance_service.add_credits(user.id, bonus_credits, "daily_bonus")

        self.repo.db.commit()
        
        # Check achievements (streak)
        newly_earned = []
        try:
            from bot.services.achievements import check_and_award_achievements
            newly_earned = check_and_award_achievements(
                db=self.repo.db,
                user_id=user.id,
                telegram_id=user.telegram_user_id,
                lang=user.language_code or "ru"
            )
            self.repo.db.commit()
        except Exception as e:
            logger.error(f"Error checking achievements for user {user.id}: {e}")

        return {
            "success": True,
            "credits": bonus_credits,
            "streak": user.daily_streak,
            "balance": self.balance_service.get_balance_value(user.id),
            "newly_earned": newly_earned
        }
