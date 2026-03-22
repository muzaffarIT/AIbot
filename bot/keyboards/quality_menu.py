from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from shared.utils.i18n import I18n

i18n = I18n()

def get_quality_keyboard(provider: str, lang: str) -> InlineKeyboardMarkup:
    """Returns inline keyboard for quality selection based on provider and language."""
    buttons = []
    
    if provider == "nano_banana":
        buttons = [
            [InlineKeyboardButton(text=i18n.t(lang, "quality.nano.standard"), callback_data="q:nano:std")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.nano.hd"), callback_data="q:nano:hd")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.nano.4k"), callback_data="q:nano:4k")],
        ]
    elif provider == "veo":
        buttons = [
            [InlineKeyboardButton(text=i18n.t(lang, "quality.veo.fast"), callback_data="q:veo:fast")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.veo.quality"), callback_data="q:veo:quality")],
        ]
    elif provider == "kling":
        buttons = [
            [InlineKeyboardButton(text=i18n.t(lang, "quality.kling.std5"), callback_data="q:kling:std5")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.kling.pro5"), callback_data="q:kling:pro5")],
            [InlineKeyboardButton(text=i18n.t(lang, "quality.kling.pro10"), callback_data="q:kling:pro10")],
        ]
    
    buttons.append([InlineKeyboardButton(text=i18n.t(lang, "common.cancel"), callback_data="start_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

QUALITY_DATA = {
    "nano:std": {"cost": 5, "payload": {"image_size": "1:1"}},
    "nano:hd": {"cost": 10, "payload": {"image_size": "1536x1536"}},
    "nano:4k": {"cost": 20, "payload": {"image_size": "2048x2048"}}, # Adjusted cost to 20
    
    "veo:fast": {"cost": 30, "payload": {"model": "veo3_fast"}},
    "veo:quality": {"cost": 80, "payload": {"model": "veo3_quality"}}, # Adjusted cost to 80
    
    "kling:std5": {"cost": 40, "payload": {"mode": "std", "duration": "5"}},
    "kling:pro5": {"cost": 70, "payload": {"mode": "pro", "duration": "5"}},
    "kling:pro10": {"cost": 120, "payload": {"mode": "pro", "duration": "10"}},
}
