from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from bot.keyboards.main_menu import main_inline_keyboard

router = Router()

TERMS_TEXT = """📄 <b>Пользовательское соглашение BATIR AI</b>

<b>1. Общие положения</b>
Используя бота BATIR AI, вы соглашаетесь с настоящими условиями.
Сервис предоставляется «как есть» без гарантий результата.

<b>2. Кредиты и оплата</b>
• Кредиты приобретаются за Telegram Stars
• Кредиты не возвращаются после успешной генерации
• При технической ошибке кредиты возвращаются автоматически
• Кредиты не имеют срока действия

<b>3. Контент</b>
• Вы несёте ответственность за содержание промптов
• Запрещено генерировать контент 18+, насилие, незаконные материалы
• Мы вправе заблокировать аккаунт за нарушения

<b>4. Партнёрская программа</b>
• 20 кредитов начисляются за первую покупку реферала
• Реферальные кредиты не выводятся в деньги
• Мошеннические схемы приведут к блокировке

<b>5. Конфиденциальность</b>
• Мы храним только Telegram ID и историю генераций
• Данные не передаются третьим лицам
• История генераций хранится 30 дней

<b>6. Поддержка</b>
Контакт: @khaetov_000

<b>7. Изменения</b>
Мы вправе обновлять соглашение.
Продолжая использовать бот — вы принимаете изменения.
"""


@router.message(Command("terms"))
async def show_terms(message: Message) -> None:
    await message.answer(
        TERMS_TEXT,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принимаю", callback_data="start_menu")],
        ]),
    )


@router.callback_query(F.data == "menu_terms")
async def show_terms_callback(callback) -> None:
    await callback.message.answer(
        TERMS_TEXT,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принимаю", callback_data="start_menu")],
        ]),
    )
    await callback.answer()
