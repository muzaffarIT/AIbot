"""
Credit packages for HARF AI (Telegram Stars payments).
"""

import json
from aiogram import Bot
from aiogram.types import LabeledPrice
from backend.services.balance_service import BalanceService
from bot.services.db_session import get_db_session

PACKAGES = {
    "start": {
        "name": "⚡ Start",
        "description": "100 кредитов. ~20 картинок Nano Banana или 3 видео Veo fast.",
        "credits": 100,
        "stars": 580,
        "price_usd": "$7.50",
    },
    "pro": {
        "name": "💎 Pro",
        "description": "300 кредитов. ~60 картинок или 10 видео Veo fast. Популярный выбор.",
        "credits": 300,
        "stars": 1450,
        "price_usd": "$19.00",
    },
    "creator": {
        "name": "🚀 Creator",
        "description": "600 кредитов. ~120 картинок или 20 видео Veo.",
        "credits": 600,
        "stars": 2600,
        "price_usd": "$34.00",
    },
    "ultra": {
        "name": "👑 Ultra",
        "description": "1500 кредитов. Максимальный пакет для профессионалов.",
        "credits": 1500,
        "stars": 5800,
        "price_usd": "$75.00",
    },
}


class BotPaymentService:
    @staticmethod
    async def send_invoice(bot: Bot, chat_id: int, package_id: str) -> None:
        if package_id not in PACKAGES:
            raise ValueError(f"Unknown package id: {package_id}")

        pkg = PACKAGES[package_id]

        await bot.send_invoice(
            chat_id=chat_id,
            title=pkg["name"],
            description=pkg["description"],
            payload=f"credits:{package_id}:{pkg['credits']}",
            provider_token="",   # Empty = Telegram Stars
            currency="XTR",      # XTR = Telegram Stars
            prices=[LabeledPrice(label=pkg["name"], amount=pkg["stars"])],
        )

    @staticmethod
    def process_successful_payment(user_id: int, payload: str) -> int:
        """
        Parse payload like 'credits:pro:300' and credit the user's wallet.
        Returns the credited amount.
        """
        parts = payload.split(":")
        if len(parts) != 3 or parts[0] != "credits":
            return 0

        try:
            amount = int(parts[2])
        except ValueError:
            return 0

        db = get_db_session()
        result_amount = 0
        try:
            balance_service = BalanceService(db)
            balance_service.add_credits(user_id, amount, "telegram_stars_purchase")
            db.commit()
            result_amount = amount
        except Exception as e:
            print(f"Failed to credit: {e}")
            db.rollback()
        finally:
            db.close()
        return result_amount
