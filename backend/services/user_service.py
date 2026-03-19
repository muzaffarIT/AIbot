from sqlalchemy.orm import Session

from backend.db.repositories.users import UserRepository
from backend.services.balance_service import BalanceService
from backend.models.user import User
from backend.core.config import settings


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
                language_code=language_code,
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
