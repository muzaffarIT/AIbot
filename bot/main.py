import asyncio
import os
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from backend.db.init_db import init_db
from bot.handlers.veo import router as veo_router  # handles F.photo, veo, AND kling
from bot.handlers.nanobanana import router as nanobanana_router
from bot.handlers.jobs import router as jobs_router
from bot.handlers.balance import router as balance_router
from bot.handlers.payments import router as payments_router
from bot.handlers.start import router as start_router
from bot.handlers.callbacks import router as callbacks_router
from bot.handlers.history import router as history_router
from bot.handlers.admin import router as admin_router
from bot.middlewares.rate_limit import GenerationRateLimitMiddleware

load_dotenv()

os.makedirs("logs", exist_ok=True)
file_handler = RotatingFileHandler("logs/errors.log", maxBytes=10*1024*1024, backupCount=5)
file_handler.setLevel(logging.ERROR)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logging.getLogger().addHandler(file_handler)


async def main() -> None:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")

    init_db()

    bot = Bot(token=bot_token)
    dp = Dispatcher()
    dp.message.middleware(GenerationRateLimitMiddleware(limit=3, interval=60))

    dp.include_router(start_router)      # /start command
    dp.include_router(callbacks_router)   # all inline callbacks
    dp.include_router(payments_router)    # Stars payment events
    dp.include_router(veo_router)         # F.photo + Veo + Kling prompt states
    dp.include_router(nanobanana_router)  # Nano Banana prompt state
    dp.include_router(jobs_router)
    dp.include_router(balance_router)
    dp.include_router(history_router)
    dp.include_router(admin_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
