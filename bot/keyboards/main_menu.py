from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from backend.core.config import settings


def main_inline_keyboard() -> InlineKeyboardMarkup:
    """Main menu inline keyboard — used everywhere instead of ReplyKeyboardMarkup."""
    miniapp_url = (settings.miniapp_url or "").rstrip("/")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎨 Создать", callback_data="menu_create"),
                InlineKeyboardButton(text="💎 Тарифы", callback_data="menu_plans"),
            ],
            [
                InlineKeyboardButton(text="📊 Мои работы", callback_data="history_cmd"),
                InlineKeyboardButton(text="💰 Баланс", callback_data="menu_balance"),
            ],
            [
                InlineKeyboardButton(text="👥 Партнёрам", callback_data="menu_referral"),
                InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help"),
            ],
            [
                InlineKeyboardButton(
                    text="🌐 Открыть кабинет",
                    web_app=WebAppInfo(url=miniapp_url),
                ),
            ],
        ]
    )


def create_submenu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Submenu for choosing AI provider — bilingual."""
    if lang == "uz":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🍌 Nano Banana — rasm (5 kr.)", callback_data="gen_start:nano_banana")],
                [InlineKeyboardButton(text="🎬 Veo 3 — video 8s Google (30 kr.)", callback_data="gen_start:veo")],
                [InlineKeyboardButton(text="🎥 Kling Motion — video (40 kr.)", callback_data="gen_start:kling")],
                [InlineKeyboardButton(text="✨ Meni hayrat qoldiring", callback_data="surprise_me")],
                [InlineKeyboardButton(text="← Orqaga", callback_data="start_menu")],
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍌 Nano Banana — картинка (5 кр.)", callback_data="gen_start:nano_banana")],
            [InlineKeyboardButton(text="🎬 Veo 3 — видео 8 сек (30 кр.)", callback_data="gen_start:veo")],
            [InlineKeyboardButton(text="🎥 Kling Motion — видео (40 кр.)", callback_data="gen_start:kling")],
            [InlineKeyboardButton(text="✨ Удиви меня", callback_data="surprise_me")],
            [InlineKeyboardButton(text="← Назад", callback_data="start_menu")],
        ]
    )
