from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from backend.core.config import settings
from shared.utils.i18n import I18n

i18n = I18n()

def welcome_inline_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.t(lang, 'start.launch_app'),
                    web_app=WebAppInfo(url=settings.miniapp_url.rstrip('/'))
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"💎 {i18n.t(lang, 'menu.buy')}",
                    callback_data="buy_credits"
                ),
                InlineKeyboardButton(
                    text=f"📊 {i18n.t(lang, 'menu.history')}",
                    callback_data="history_cmd"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"👨‍💻 {i18n.t(lang, 'menu.support')}",
                    url="https://t.me/muzaffar_it"
                )
            ]
        ]
    )
