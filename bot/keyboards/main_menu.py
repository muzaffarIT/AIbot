from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from backend.core.config import settings


def main_inline_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Main menu — bilingual (ru/uz).

    Mini-app first: the AI chat (models, image/video generation, history,
    voice) lives in the mini app, so it gets the top, full-width slot. The
    older in-bot generation flow stays available underneath as a fallback for
    clients where the mini app misbehaves — but it is no longer the default
    path, which kept it drifting out of sync with the app.
    """
    miniapp_url = (settings.miniapp_url or "").rstrip("/")
    if lang == "uz":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✨ HARF AI'ni ochish",
                        web_app=WebAppInfo(url=miniapp_url),
                    ),
                ],
                [
                    InlineKeyboardButton(text="💎 Tariflar", callback_data="menu_plans"),
                    InlineKeyboardButton(text="💰 Balans", callback_data="menu_balance"),
                ],
                [
                    InlineKeyboardButton(text="📊 Ishlarim", callback_data="history_cmd"),
                    InlineKeyboardButton(text="👥 Hamkorlik", callback_data="menu_referral"),
                ],
                [
                    InlineKeyboardButton(text="🎨 Botda yaratish", callback_data="menu_create"),
                    InlineKeyboardButton(text="✨ Namunalar", callback_data="menu_showcase"),
                ],
                [
                    InlineKeyboardButton(text="🔔 Bildirishnomalar", callback_data="menu_notifications"),
                    InlineKeyboardButton(text="❓ Yordam", callback_data="menu_help"),
                    InlineKeyboardButton(text="🌍 Til: O'zbek 🇺🇿", callback_data="menu_language"),
                ],
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ Открыть HARF AI",
                    web_app=WebAppInfo(url=miniapp_url),
                ),
            ],
            [
                InlineKeyboardButton(text="💎 Тарифы", callback_data="menu_plans"),
                InlineKeyboardButton(text="💰 Баланс", callback_data="menu_balance"),
            ],
            [
                InlineKeyboardButton(text="📊 Мои работы", callback_data="history_cmd"),
                InlineKeyboardButton(text="👥 Партнёрам", callback_data="menu_referral"),
            ],
            [
                InlineKeyboardButton(text="🎨 Создать в боте", callback_data="menu_create"),
                InlineKeyboardButton(text="✨ Примеры", callback_data="menu_showcase"),
            ],
            [
                InlineKeyboardButton(text="🔔 Уведомления", callback_data="menu_notifications"),
                InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help"),
                InlineKeyboardButton(text="🌍 Язык: Русский 🇷🇺", callback_data="menu_language"),
            ],
        ]
    )


def create_submenu_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    """Submenu for choosing AI provider — bilingual.

    Image tiers are flat ("tier:..." callback): one tap = pick model + quality,
    then bot asks for prompt. Video providers keep a nested quality submenu
    ("gen_start:..." callback) because duration/resolution choice is load-bearing.
    """
    if lang == "uz":
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🍌 Nano Banana · 1K · 10 kr.", callback_data="tier:nano:std")],
                [InlineKeyboardButton(text="✨ Nano Banana 2 · 2K · 20 kr.", callback_data="tier:nano:hd")],
                [InlineKeyboardButton(text="⭐ Nano Banana Pro 2K · 30 kr.", callback_data="tier:nano:pro_hd")],
                [InlineKeyboardButton(text="👑 Nano Banana Pro 4K · 50 kr.", callback_data="tier:nano:4k")],
                [InlineKeyboardButton(text="🎨 GPT Image 2 · 30 kr.", callback_data="tier:gpt:std")],
                [InlineKeyboardButton(text="🎬 Veo 3 — video (30–90 kr.)", callback_data="gen_start:veo")],
                [InlineKeyboardButton(text="🎥 Kling Motion — video (40–120 kr.)", callback_data="gen_start:kling")],
                [InlineKeyboardButton(text="← Orqaga", callback_data="start_menu")],
            ]
        )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🍌 Nano Banana · 1K · 10 кр.", callback_data="tier:nano:std")],
            [InlineKeyboardButton(text="✨ Nano Banana 2 · 2K · 20 кр.", callback_data="tier:nano:hd")],
            [InlineKeyboardButton(text="⭐ Nano Banana Pro 2K · 30 кр.", callback_data="tier:nano:pro_hd")],
            [InlineKeyboardButton(text="👑 Nano Banana Pro 4K · 50 кр.", callback_data="tier:nano:4k")],
            [InlineKeyboardButton(text="🎨 GPT Image 2 · 30 кр.", callback_data="tier:gpt:std")],
            [InlineKeyboardButton(text="🎬 Veo 3 — видео (30–90 кр.)", callback_data="gen_start:veo")],
            [InlineKeyboardButton(text="🎥 Kling Motion — видео (40–120 кр.)", callback_data="gen_start:kling")],
            [InlineKeyboardButton(text="← Назад", callback_data="start_menu")],
        ]
    )
