import json
from aiogram import Bot
from aiogram.types import LabeledPrice
from backend.services.balance_service import BalanceService
from bot.services.db_session import get_db_session

# TODO: заменить на Click/Payme когда будет ИП
# Click docs: https://docs.click.uz
# Payme docs: https://developer.payme.uz

PACKAGES = {
    "start": {
        "title": "⚡ Стартер",
        "description": "50 кредитов для старта",
        "credits": 50,
        "stars": 400
    },
    "basic": {
        "title": "🔥 Базовый",
        "description": "150 кредитов для активного использования",
        "credits": 150,
        "stars": 950
    },
    "pro": {
        "title": "💎 Про",
        "description": "500 кредитов для продвинутых",
        "credits": 500,
        "stars": 2500
    },
    "creator": {
        "title": "🚀 Криэйтор",
        "description": "1500 кредитов для профи",
        "credits": 1500,
        "stars": 6500
    }
}

class BotPaymentService:
    @staticmethod
    async def send_invoice(bot: Bot, chat_id: int, package_id: str) -> None:
        if package_id not in PACKAGES:
            raise ValueError("Unknown package id")
            
        pkg = PACKAGES[package_id]
        
        await bot.send_invoice(
            chat_id=chat_id,
            title=pkg["title"],
            description=pkg["description"],
            payload=f"credits:{package_id}:{pkg['credits']}",
            provider_token="",  # пустая строка = Telegram Stars
            currency="XTR",     # XTR = Telegram Stars
            prices=[LabeledPrice(label="Stars", amount=pkg["stars"])]
        )
        
    @staticmethod
    def process_successful_payment(user_id: int, payload: str) -> int:
        """
        Parses payload like 'credits:pro:500' and credits the user's wallet.
        Returns the credited amount.
        """
        parts = payload.split(":")
        if len(parts) != 3 or parts[0] != "credits":
            return 0
            
        amount = int(parts[2])
        
        db = get_db_session()
        try:
            balance_service = BalanceService(db)
            balance_service.add_credits(user_id, amount, "telegram_stars_purchase")
            db.commit()
            return amount
        except Exception as e:
            print(f"Failed to credit: {e}")
            db.rollback()
            return 0
        finally:
            db.close()
