from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from shared.utils.i18n import I18n

i18n = I18n()


def main_menu_keyboard(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=i18n.t(lang, "menu.generate_image")),
                KeyboardButton(text=i18n.t(lang, "menu.animate_image")),
            ],
            [
                KeyboardButton(text=i18n.t(lang, "menu.create_video")),
                KeyboardButton(text=i18n.t(lang, "menu.jobs")),
            ],
            [
                KeyboardButton(text=i18n.t(lang, "menu.balance")),
                KeyboardButton(text=i18n.t(lang, "menu.buy")),
            ],
            [
                KeyboardButton(text=i18n.t(lang, "menu.open_cabinet")),
            ],
            [
                KeyboardButton(text=i18n.t(lang, "menu.language")),
            ],
        ],
        resize_keyboard=True,
    )
