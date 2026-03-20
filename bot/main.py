import asyncio
import os
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from backend.db.init_db import init_db

# ORDER IS CRITICAL:
from bot.handlers.payments import router as payments_router       # F.successful_payment MUST be first
from bot.handlers.daily import router as daily_router             # ☀️ Bonus reply btn + /daily
from bot.handlers.start import router as start_router             # /start + CommandStart
from bot.handlers.reply_router import router as reply_router      # All reply keyboard buttons
from bot.handlers.help import router as help_router               # /help
from bot.handlers.terms import router as terms_router             # /terms
from bot.handlers.referral import router as referral_router       # /referral
from bot.handlers.achievements import router as achievements_router  # /achievements
from bot.handlers.callbacks import router as callbacks_router     # all inline keyboard callbacks
from bot.handlers.veo import router as veo_router                 # F.photo + veo + kling FSM states
from bot.handlers.nanobanana import router as nanobanana_router   # nano banana FSM state
from bot.handlers.jobs import router as jobs_router
from bot.handlers.balance import router as balance_router
from bot.handlers.history import router as history_router
from bot.handlers.admin import router as admin_router
from bot.middlewares.rate_limit import GenerationRateLimitMiddleware

load_dotenv()

os.makedirs("logs", exist_ok=True)
_file_handler = RotatingFileHandler("logs/errors.log", maxBytes=10 * 1024 * 1024, backupCount=5)
_file_handler.setLevel(logging.ERROR)
_formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
_file_handler.setFormatter(_formatter)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), _file_handler],
)


async def main() -> None:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")

    init_db()

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp.message.middleware(GenerationRateLimitMiddleware(limit=3, interval=60))

    dp.include_router(payments_router)     # F.successful_payment / pre_checkout — FIRST
    dp.include_router(daily_router)        # ☀️ Bonus reply + /daily — before generic reply_router
    dp.include_router(start_router)        # /start
    dp.include_router(reply_router)        # all other reply keyboard buttons
    dp.include_router(help_router)         # /help
    dp.include_router(terms_router)        # /terms
    dp.include_router(referral_router)     # /referral
    dp.include_router(achievements_router)  # /achievements
    dp.include_router(callbacks_router)    # inline keyboard callbacks
    dp.include_router(veo_router)          # F.photo + veo + kling FSM
    dp.include_router(nanobanana_router)   # nano banana FSM
    dp.include_router(jobs_router)
    dp.include_router(balance_router)
    dp.include_router(history_router)
    dp.include_router(admin_router)

    logging.info(f"[BOT] Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
