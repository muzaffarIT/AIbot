from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_telegram_user_id(self, telegram_user_id: int) -> User | None:
        stmt = select(User).where(User.telegram_user_id == telegram_user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_referral_code(self, code: str) -> User | None:
        stmt = select(User).where(User.referral_code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_referral_count(self, user_id: int) -> int:
        # Count users whose referred_by_telegram_id matches this user's telegram_user_id
        user = self.db.get(User, user_id)
        if not user:
            return 0
        count = self.db.execute(
            select(User).where(User.referred_by_telegram_id == user.telegram_user_id)
        ).scalars().all()
        return len(count)

    def create_user(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str = "ru",
    ) -> User:
        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_profile(
        self,
        user: User,
        *,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> User:
        if username is not None:
            user.username = username
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if language_code:
            user.language_code = language_code

        self.db.commit()
        self.db.refresh(user)
        return user

    def update_language(self, user: User, language_code: str) -> User:
        user.language_code = language_code
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_referred_by(self, user_id: int, referrer_telegram_id: int) -> None:
        user = self.db.get(User, user_id)
        if user and not user.referred_by_telegram_id:
            user.referred_by_telegram_id = referrer_telegram_id
            self.db.commit()


    def create_user(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str = "ru",
    ) -> User:
        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_profile(
        self,
        user: User,
        *,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> User:
        if username is not None:
            user.username = username
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if language_code:
            user.language_code = language_code

        self.db.commit()
        self.db.refresh(user)
        return user

    def update_language(self, user: User, language_code: str) -> User:
        user.language_code = language_code
        self.db.commit()
        self.db.refresh(user)
        return user
