from aiogram import F, Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

from bot.keyboards.main_menu import main_inline_keyboard

router = Router()

HELP_TEXT = """❓ <b>Помощь и поддержка BATIR AI</b>

<b>Как пользоваться:</b>
1. Нажми 🎨 Создать
2. Выбери нейросеть
3. Напиши промпт на <b>английском</b>
4. Дождись результата (от 30 сек до 5 мин)

<b>Нейросети:</b>
🍌 <b>Nano Banana</b> — картинки (5 кр.)
🎬 <b>Veo 3</b> — видео 8 сек от Google (30 кр.)
🎥 <b>Kling Motion</b> — видео высокого качества (40 кр.)

<b>Советы для промптов:</b>
• Пиши на английском
• Добавляй: 4k, cinematic, realistic, detailed
• Для видео: slow motion, close-up, aerial view

<b>Примеры:</b>
🖼 "a futuristic city at night, neon lights, 4k, cinematic"
🎬 "a whale swimming in the ocean, slow motion, nature documentary"

<b>Загрузка фото:</b>
Отправь фото + промпт в подписи — модель оживит твоё изображение

<b>Партнёрская программа:</b>
Используй /referral чтобы приглашать друзей
и получать 20 кредитов за каждого!

<b>Проблемы?</b>
Напиши нам: @khaetov_000
"""


@router.message(Command("help"))
async def show_help_cmd(message: Message) -> None:
    await message.answer(
        HELP_TEXT,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать поддержке", url="https://t.me/khaetov_000")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start_menu")],
        ]),
    )


@router.callback_query(F.data == "menu_help")
async def show_help_callback(callback: CallbackQuery) -> None:
    await callback.message.answer(
        HELP_TEXT,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать поддержке", url="https://t.me/khaetov_000")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="start_menu")],
        ]),
    )
    await callback.answer()
