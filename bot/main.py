import asyncio
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from backend.db.init_db import init_db
from bot.handlers.kling import router as kling_router
from bot.handlers.nanobanana import router as nanobanana_router
from bot.handlers.veo import router as veo_router
from bot.handlers.jobs import router as jobs_router
from bot.handlers.balance import router as balance_router
from bot.handlers.payments import router as payments_router
from bot.handlers.start import router as start_router

load_dotenv()


async def main() -> None:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is not set")

    init_db()

    bot = Bot(token=bot_token)
    dp = Dispatcher()

    dp.include_router(nanobanana_router)
    dp.include_router(kling_router)
    dp.include_router(veo_router)
    dp.include_router(jobs_router)
    dp.include_router(balance_router)
    dp.include_router(payments_router)
    dp.include_router(start_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
