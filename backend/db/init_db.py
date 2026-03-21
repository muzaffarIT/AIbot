from backend.db.base import Base
from backend.db.session import engine
from backend.db.session import SessionLocal
from backend import models  # noqa: F401
from backend.services.plan_service import PlanService


def _run_migrations(db) -> None:
    """Add new columns/tables idempotently at startup (safe to run multiple times)."""
    from sqlalchemy import text

    migrations = [
        # Referral system columns on users table
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(16) UNIQUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by_telegram_id BIGINT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_earnings INTEGER DEFAULT 0 NOT NULL",
        # Backfill referral_code for existing users
        "UPDATE users SET referral_code = upper(substr(md5(telegram_user_id::text), 1, 8)) WHERE referral_code IS NULL",
        # Daily streak columns
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_daily_claim TIMESTAMPTZ",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_streak INTEGER DEFAULT 0 NOT NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS max_streak INTEGER DEFAULT 0 NOT NULL",
        # Notifications
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_notification_at TIMESTAMPTZ",
        # Onboarding
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed BOOLEAN DEFAULT FALSE NOT NULL",
        # Achievements table
        """CREATE TABLE IF NOT EXISTS achievements (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            achievement_code VARCHAR(64) NOT NULL,
            earned_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS ix_achievements_user_id ON achievements (user_id)",
        """CREATE TABLE IF NOT EXISTS settings (
            key VARCHAR(100) PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
        )""",
    ]
    for sql in migrations:
        try:
            db.execute(text(sql))
        except Exception:
            db.rollback()  # rollback bad statement individually
    db.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _run_migrations(db)
        PlanService(db).seed_default_plans()
    finally:
        db.close()
