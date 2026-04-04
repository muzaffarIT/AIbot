"""
Language selection handler.
User picks ru/uz → saved to DB → miniapp picks it up on next sync automatically.
"""
import logging
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommandScopeChat, BotCommand

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router()

LANG_SELECT_KB = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
        InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="set_lang:uz"),
    ]
])


@router.callback_query(F.data == "menu_language")
async def menu_language(callback: CallbackQuery) -> None:
    await callback.message.answer(
        "🌍 Выберите язык интерфейса / Interfeys tilini tanlang:",
        reply_markup=LANG_SELECT_KB,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_lang:"))
async def set_language(callback: CallbackQuery) -> None:
    lang = callback.data.split(":")[1]
    if lang not in ("ru", "uz"):
        await callback.answer("❌ Unknown language", show_alert=True)
        return

    db = get_db_session()
    try:
        user_service = UserService(db)
        user_service.set_user_language(callback.from_user.id, lang)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"set_language error: {e}")
        await callback.answer("❌ Ошибка сохранения", show_alert=True)
        return
    finally:
        db.close()

    from bot.keyboards.main_menu import main_inline_keyboard
    from bot.keyboards.reply_menu import main_reply_keyboard

    chat_id = callback.from_user.id

    if lang == "uz":
        # Hide bot command menu for Uzbek — only reply keyboard buttons shown
        try:
            await callback.bot.set_my_commands(
                [],
                scope=BotCommandScopeChat(chat_id=chat_id),
            )
        except Exception as e:
            logger.warning(f"set_my_commands(uz) failed: {e}")

        text = (
            "✅ <b>Til o'zgartirildi: O'zbek 🇺🇿</b>\n\n"
            "Mini App ham keyingi ochilganda avtomatik o'zbek tiliga o'tadi."
        )
    else:
        # Restore default commands for Russian
        try:
            ru_commands = [
                BotCommand(command="start", description="Главное меню"),
                BotCommand(command="help", description="Помощь"),
                BotCommand(command="balance", description="Баланс"),
                BotCommand(command="referral", description="Реферальная программа"),
            ]
            await callback.bot.set_my_commands(
                ru_commands,
                scope=BotCommandScopeChat(chat_id=chat_id),
            )
        except Exception as e:
            logger.warning(f"set_my_commands(ru) failed: {e}")

        text = (
            "✅ <b>Язык изменён: Русский 🇷🇺</b>\n\n"
            "МиниЭп тоже автоматически переключится при следующем открытии."
        )

    await callback.message.answer(text, reply_markup=main_reply_keyboard(lang), parse_mode="HTML")
    await callback.answer()
