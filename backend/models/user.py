from datetime import datetime
import uuid

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


def _gen_ref_code() -> str:
    return uuid.uuid4().hex[:8].upper()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="ru", nullable=False)

    # Referral system
    referral_code: Mapped[str] = mapped_column(
        String(16), unique=True, index=True, nullable=False, default=_gen_ref_code
    )
    referred_by_telegram_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    referral_earnings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )