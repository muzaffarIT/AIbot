"""
Quality/mode selection keyboards for each AI provider.
Shown after user picks a provider, before they enter a prompt.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def nano_quality_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Quality options for Nano Banana image generation."""
    if lang == "uz":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🖼 Standart · 1024px · 5 kr.", callback_data="nano_quality:standard")],
            [InlineKeyboardButton(text="✨ HD · 1536px · 10 kr.", callback_data="nano_quality:hd")],
            [InlineKeyboardButton(text="💎 4K · 2048px · 20 kr.", callback_data="nano_quality:4k")],
            [InlineKeyboardButton(text="← Orqaga", callback_data="start_menu")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼 Стандарт · 1024px · 5 кр.", callback_data="nano_quality:standard")],
        [InlineKeyboardButton(text="✨ HD · 1536px · 10 кр.", callback_data="nano_quality:hd")],
        [InlineKeyboardButton(text="💎 4K · 2048px · 20 кр.", callback_data="nano_quality:4k")],
        [InlineKeyboardButton(text="← Назад", callback_data="start_menu")],
    ])


def veo_quality_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Quality options for Veo 3 video generation."""
    if lang == "uz":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Fast · 8 son. · 720p · 30 kr.", callback_data="veo_quality:fast")],
            [InlineKeyboardButton(text="💎 Quality · 8 son. · 1080p · 80 kr.", callback_data="veo_quality:quality")],
            [InlineKeyboardButton(text="← Orqaga", callback_data="start_menu")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Fast · 8 сек · 720p · 30 кр.", callback_data="veo_quality:fast")],
        [InlineKeyboardButton(text="💎 Quality · 8 сек · 1080p · 80 кр.", callback_data="veo_quality:quality")],
        [InlineKeyboardButton(text="← Назад", callback_data="start_menu")],
    ])


def kling_quality_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Quality options for Kling Motion video generation."""
    if lang == "uz":
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎬 Standart · 5 son. · 720p · 40 kr.", callback_data="kling_quality:std:5")],
            [InlineKeyboardButton(text="✨ Pro · 5 son. · 1080p · 70 kr.", callback_data="kling_quality:pro:5")],
            [InlineKeyboardButton(text="👑 Pro · 10 son. · 1080p · 120 kr.", callback_data="kling_quality:pro:10")],
            [InlineKeyboardButton(text="🔥 Pro Max · 15 son. · 1080p · 180 kr.", callback_data="kling_quality:pro:15")],
            [InlineKeyboardButton(text="← Orqaga", callback_data="start_menu")],
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Стандарт · 5 сек · 720p · 40 кр.", callback_data="kling_quality:std:5")],
        [InlineKeyboardButton(text="✨ Pro · 5 сек · 1080p · 70 кр.", callback_data="kling_quality:pro:5")],
        [InlineKeyboardButton(text="👑 Pro · 10 сек · 1080p · 120 кр.", callback_data="kling_quality:pro:10")],
        [InlineKeyboardButton(text="🔥 Pro Max · 15 сек · 1080p · 180 кр.", callback_data="kling_quality:pro:15")],
        [InlineKeyboardButton(text="← Назад", callback_data="start_menu")],
    ])


# Quality → (cost_credits, payload_overrides)
NANO_QUALITY_MAP = {
    "standard": (5,  {"width": 1024, "height": 1024}),
    "hd":       (10, {"width": 1536, "height": 1536}),
    "4k":       (20, {"width": 2048, "height": 2048}),
}

VEO_QUALITY_MAP = {
    "fast":    (30, {"quality": "fast",    "duration": 8}),
    "quality": (80, {"quality": "quality", "duration": 8}),
}

KLING_QUALITY_MAP = {
    "std:5":  (40,  {"mode": "std", "duration": 5}),
    "pro:5":  (70,  {"mode": "pro", "duration": 5}),
    "pro:10": (120, {"mode": "pro", "duration": 10}),
    "pro:15": (180, {"mode": "pro", "duration": 15}),
}
