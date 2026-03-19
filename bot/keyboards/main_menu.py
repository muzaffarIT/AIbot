from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from shared.utils.i18n import I18n
from backend.core.config import settings

i18n = I18n()


def main_menu_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()

    builder.row(
        KeyboardButton(
            text=i18n.t(lang, "menu.open_cabinet"),
            web_app=WebAppInfo(url=settings.miniapp_url + "/"),
        )
    )

    builder.row(
        KeyboardButton(text=i18n.t(lang, "menu.generate_image")),
        KeyboardButton(text=i18n.t(lang, "menu.create_video")),
    )
    
    builder.row(
        KeyboardButton(text=i18n.t(lang, "menu.animate_image")),
        KeyboardButton(text=i18n.t(lang, "menu.jobs")),
    )

    builder.row(
        KeyboardButton(text=i18n.t(lang, "menu.buy")),
        KeyboardButton(text=i18n.t(lang, "menu.balance")),
    )
    
    builder.row(
        KeyboardButton(text=i18n.t(lang, "menu.language")),
    )

    return builder.as_markup(resize_keyboard=True)
