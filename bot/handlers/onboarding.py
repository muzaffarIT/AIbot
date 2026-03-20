"""
Onboarding flow for new users: 4 steps with 1.5s delay.
Triggered from start.py after first registration.
"""
import asyncio
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)
i18n = I18n()


async def run_onboarding(bot: Bot, chat_id: int, name: str, lang: str = "ru") -> None:
    """Send 4 onboarding messages with 1.5s delays."""
    try:
        # Step 1 — immediate (welcome already sent by start.py, this adds context)
        await asyncio.sleep(1.5)
        await bot.send_message(
            chat_id,
            i18n.t(lang, "onboarding.step2"),
        )

        # Step 2 — model descriptions
        await asyncio.sleep(1.5)
        surprise_btn = i18n.t(lang, "onboarding.btn.surprise")
        nano_btn = i18n.t(lang, "onboarding.btn.try_nano")
        await bot.send_message(
            chat_id,
            i18n.t(lang, "onboarding.step3"),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=nano_btn, callback_data="gen_start:nano_banana"),
                    InlineKeyboardButton(text=surprise_btn, callback_data="surprise_me"),
                ]
            ]),
        )
    except Exception as e:
        logger.error(f"[Onboarding] Failed for chat_id={chat_id}: {e}")


async def send_post_first_gen_message(bot: Bot, chat_id: int, lang: str = "ru") -> None:
    """Step 4: sent after the user's first generation completes."""
    try:
        await bot.send_message(chat_id, i18n.t(lang, "onboarding.step4"))
    except Exception as e:
        logger.error(f"[Onboarding step4] Failed for chat_id={chat_id}: {e}")
