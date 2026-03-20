from backend.db.base import Base
from backend.db.session import engine
from backend.db.session import SessionLocal
from backend import models  # noqa: F401
from backend.services.plan_service import PlanService


def _run_migrations(db) -> None:
    """Add new columns to existing tables if they don't exist (safe idempotent migration)."""
    from sqlalchemy import text
    migrations = [
        # Referral system columns on users table
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(16) UNIQUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by_telegram_id BIGINT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_earnings INTEGER DEFAULT 0 NOT NULL",
        # Backfill referral_code for existing users (generate random codes)
        "UPDATE users SET referral_code = upper(substr(md5(telegram_user_id::text), 1, 8)) WHERE referral_code IS NULL",
    ]
    for sql in migrations:
        try:
            db.execute(text(sql))
        except Exception:
            pass  # Column already exists or other harmless error
    db.commit()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        _run_migrations(db)
        PlanService(db).seed_default_plans()
    finally:
        db.close()
