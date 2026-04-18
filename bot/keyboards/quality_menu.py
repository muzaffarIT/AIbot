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
    
    back_text = "← Orqaga" if lang == "uz" else "← Назад"
    buttons.append([InlineKeyboardButton(text=back_text, callback_data="menu_create")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

QUALITY_DATA = {
    # Nano Banana — 3 different models for cost efficiency:
    # nano-banana        = 4 kie.ai credits ($0.02)  → Standard 1K
    # nano-banana-2      = 12 kie.ai credits ($0.06)  → HD 2K
    # nano-banana-pro    = 24 kie.ai credits ($0.12)  → 4K Ultra
    "nano:std": {"cost": 5,  "payload": {"image_size": "1024x1024", "_nano_model": "nano-banana"}},
    "nano:hd":  {"cost": 10, "payload": {"image_size": "1536x1536", "_nano_model": "nano-banana-2"}},
    "nano:4k":  {"cost": 20, "payload": {"image_size": "2048x2048", "_nano_model": "nano-banana-pro"}},

    # Veo 3 — veo3_fast=80 kie credits ($0.40), veo3_quality=400 kie credits ($2.00)
    "veo:fast":    {"cost": 30, "payload": {"model": "veo3_fast"}},
    "veo:quality": {"cost": 80, "payload": {"model": "veo3_quality"}},

    # Kling 3.0 — std=14 kie cr/s, pro=18 kie cr/s
    "kling:std5":  {"cost": 40,  "payload": {"mode": "std", "duration": "5"}},
    "kling:pro5":  {"cost": 70,  "payload": {"mode": "pro", "duration": "5"}},
    "kling:pro10": {"cost": 120, "payload": {"mode": "pro", "duration": "10"}},
}
