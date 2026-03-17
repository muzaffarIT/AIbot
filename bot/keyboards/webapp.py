from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo


def open_cabinet_keyboard(webapp_url: str, button_text: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=button_text,
                    web_app=WebAppInfo(url=webapp_url),
                )
            ]
        ]
    )
