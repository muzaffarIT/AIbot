from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_reply_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    """
    Persistent reply keyboard (visible at bottom of screen).
    Bilingual: RU and UZ supported.

    Layout (4 rows × 2 cols):
      🎨 Создать    | 💎 Тарифы
      📊 Мои работы | 💰 Баланс
      👥 Партнёрам  | ❓ Помощь
      ☀️ Бонус      | 🌐 Кабинет
    """
    if lang == "uz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="🎨 Yaratish"),
                    KeyboardButton(text="💎 Tariflar"),
                ],
                [
                    KeyboardButton(text="📊 Ishlarim"),
                    KeyboardButton(text="💰 Balans"),
                ],
                [
                    KeyboardButton(text="👥 Hamkorlik"),
                    KeyboardButton(text="❓ Yordam"),
                ],
                [
                    KeyboardButton(text="☀️ Bonus"),
                    KeyboardButton(text="🌐 Kabinet"),
                ],
            ],
            resize_keyboard=True,
            persistent=True,
            is_persistent=True,
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="🎨 Создать"),
                    KeyboardButton(text="💎 Тарифы"),
                ],
                [
                    KeyboardButton(text="📊 Мои работы"),
                    KeyboardButton(text="💰 Баланс"),
                ],
                [
                    KeyboardButton(text="👥 Партнёрам"),
                    KeyboardButton(text="❓ Помощь"),
                ],
                [
                    KeyboardButton(text="☀️ Бонус"),
                    KeyboardButton(text="🌐 Кабинет"),
                ],
            ],
            resize_keyboard=True,
            persistent=True,
            is_persistent=True,
        )


# Text → callback data mapping for reply keyboard button routing
REPLY_BUTTON_ACTIONS = {
    # RU
    "🎨 Создать":      "menu_create",
    "💎 Тарифы":       "menu_plans",
    "📊 Мои работы":   "history_cmd",
    "💰 Баланс":       "menu_balance",
    "👥 Партнёрам":    "menu_referral",
    "❓ Помощь":       "menu_help",
    "☀️ Бонус":        "daily_bonus",
    "🌐 Кабинет":      "open_cabinet",
    # UZ
    "🎨 Yaratish":     "menu_create",
    "💎 Tariflar":     "menu_plans",
    "📊 Ishlarim":     "history_cmd",
    "💰 Balans":       "menu_balance",
    "👥 Hamkorlik":    "menu_referral",
    "❓ Yordam":       "menu_help",
    "☀️ Bonus":        "daily_bonus",
    "🌐 Kabinet":      "open_cabinet",
}
