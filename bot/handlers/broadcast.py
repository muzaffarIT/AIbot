"""Admin broadcast — send a message to every bot user.

Flow:
  1. Admin sends `/broadcast` (or `/broadcast_ru` / `/broadcast_uz` to filter
     by language).
  2. Bot asks for the broadcast content.
  3. Admin sends ANY message (text / photo / video / document / voice /
     animation / sticker — anything `bot.copy_message` supports).
  4. Bot replies with a preview confirmation (count of recipients) +
     ✅ Send / ❌ Cancel buttons.
  5. On confirm — fan out via `bot.copy_message` (preserves media +
     formatting + caption). Throttled to ~25 msg/sec to stay under
     Telegram's 30 msg/sec global limit. Skips users who blocked the bot.
  6. Final report sent to admin: delivered / failed / blocked counts +
     elapsed time.

Only telegram_user_ids in `settings.admin_ids_list` can use this.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from aiogram import Bot, F, Router
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from backend.core.config import settings
from backend.models.user import User
from bot.services.db_session import get_db_session
from bot.states.broadcast_states import BroadcastStates

logger = logging.getLogger(__name__)
router = Router()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return user_id in settings.admin_ids_list


def _confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Отправить всем", callback_data="bcast:send"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="bcast:cancel"),
            ]
        ]
    )


def _fetch_recipient_ids(language_filter: Optional[str]) -> list[int]:
    """Return all telegram_user_ids matching the optional language filter."""
    db = get_db_session()
    try:
        q = db.query(User.telegram_user_id)
        if language_filter:
            q = q.filter(User.language_code == language_filter)
        return [row[0] for row in q.all()]
    finally:
        db.close()


# ── Entrypoints ──────────────────────────────────────────────────────────────

@router.message(Command("broadcast", "broadcast_ru", "broadcast_uz"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return  # silent — not an admin

    # Determine language filter from command name
    cmd = (message.text or "").split()[0].lstrip("/").split("@")[0].lower()
    language_filter: Optional[str] = None
    if cmd == "broadcast_ru":
        language_filter = "ru"
    elif cmd == "broadcast_uz":
        language_filter = "uz"

    recipients = _fetch_recipient_ids(language_filter)

    await state.clear()
    await state.update_data(
        language_filter=language_filter,
        recipient_count=len(recipients),
    )
    await state.set_state(BroadcastStates.waiting_for_message)

    filter_line = (
        f"🌐 Фильтр по языку: <b>{language_filter}</b>\n" if language_filter else ""
    )
    await message.answer(
        "📣 <b>Рассылка</b>\n\n"
        f"{filter_line}"
        f"📥 Получателей: <b>{len(recipients)}</b>\n\n"
        "Отправь следующим сообщением то, что хочешь разослать.\n"
        "Поддерживается: текст, фото, видео, документ, голосовое, анимация, стикер.\n"
        "HTML/Markdown форматирование сохраняется.\n\n"
        "Отмена: /cancel",
        parse_mode="HTML",
    )


@router.message(Command("cancel"), BroadcastStates.waiting_for_message)
@router.message(Command("cancel"), BroadcastStates.waiting_for_confirm)
async def cmd_cancel_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Рассылка отменена.")


# ── Step 2: capture content ──────────────────────────────────────────────────

@router.message(BroadcastStates.waiting_for_message)
async def capture_broadcast_message(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id if message.from_user else None):
        return

    # Save the source message coordinates so we can `copy_message` from them
    await state.update_data(
        src_chat_id=message.chat.id,
        src_message_id=message.message_id,
    )

    data = await state.get_data()
    n = data.get("recipient_count", 0)
    lang = data.get("language_filter")
    lang_line = f"🌐 Язык: <b>{lang}</b>\n" if lang else ""

    await message.reply(
        "👀 <b>Превью рассылки</b> ↑ (сообщение выше)\n\n"
        f"{lang_line}"
        f"📥 Будет отправлено: <b>{n}</b> пользователям.\n\n"
        "Подтверди отправку:",
        reply_markup=_confirm_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(BroadcastStates.waiting_for_confirm)


# ── Step 3: confirm + fan-out ────────────────────────────────────────────────

@router.callback_query(F.data == "bcast:cancel", BroadcastStates.waiting_for_confirm)
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.clear()
    try:
        await callback.message.edit_text("❌ Рассылка отменена.")
    except TelegramBadRequest:
        await callback.message.answer("❌ Рассылка отменена.")
    await callback.answer()


@router.callback_query(F.data == "bcast:send", BroadcastStates.waiting_for_confirm)
async def cb_send(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id):
        return

    data = await state.get_data()
    src_chat_id = data.get("src_chat_id")
    src_message_id = data.get("src_message_id")
    language_filter = data.get("language_filter")

    if not src_chat_id or not src_message_id:
        await callback.answer("❗ Нечего рассылать", show_alert=True)
        await state.clear()
        return

    recipients = _fetch_recipient_ids(language_filter)
    total = len(recipients)
    await state.clear()

    try:
        await callback.message.edit_text(
            f"🚀 Рассылка запущена.\nВсего: <b>{total}</b>",
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass
    await callback.answer("Запущено")

    # Spawn fan-out as background task so the callback handler returns quickly.
    asyncio.create_task(
        _run_broadcast(
            bot=bot,
            admin_chat_id=callback.from_user.id,
            src_chat_id=src_chat_id,
            src_message_id=src_message_id,
            recipients=recipients,
        )
    )


# ── Worker ───────────────────────────────────────────────────────────────────

# Telegram allows ~30 messages/second to different users. We aim for ~25/sec
# to leave headroom and avoid 429s.
_RATE_DELAY_SEC = 0.04  # 25 msg/sec
_PROGRESS_EVERY = 100   # update progress message every N sends


async def _run_broadcast(
    *,
    bot: Bot,
    admin_chat_id: int,
    src_chat_id: int,
    src_message_id: int,
    recipients: list[int],
) -> None:
    total = len(recipients)
    delivered = 0
    blocked = 0
    failed = 0
    started = time.monotonic()

    progress_msg = None
    try:
        progress_msg = await bot.send_message(
            admin_chat_id,
            f"⏳ Прогресс: 0 / {total}",
        )
    except Exception:
        progress_msg = None

    for idx, uid in enumerate(recipients, 1):
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=src_chat_id,
                message_id=src_message_id,
            )
            delivered += 1
        except TelegramForbiddenError:
            # User blocked the bot or deactivated their account
            blocked += 1
        except TelegramRetryAfter as e:
            # Hit Telegram's flood limit — back off and retry once
            wait_s = int(e.retry_after) + 1
            logger.warning("[BROADCAST] flood wait %s s", wait_s)
            await asyncio.sleep(wait_s)
            try:
                await bot.copy_message(
                    chat_id=uid,
                    from_chat_id=src_chat_id,
                    message_id=src_message_id,
                )
                delivered += 1
            except Exception as e2:
                failed += 1
                logger.warning("[BROADCAST] retry failed for %s: %s", uid, e2)
        except TelegramBadRequest as e:
            # e.g. chat not found, user_id invalid, message can't be copied
            failed += 1
            logger.debug("[BROADCAST] bad request for %s: %s", uid, e)
        except Exception as e:
            failed += 1
            logger.exception("[BROADCAST] unexpected error for %s: %s", uid, e)

        # Progress update every N
        if progress_msg is not None and idx % _PROGRESS_EVERY == 0:
            try:
                await bot.edit_message_text(
                    chat_id=admin_chat_id,
                    message_id=progress_msg.message_id,
                    text=(
                        f"⏳ Прогресс: <b>{idx}</b> / {total}\n"
                        f"✅ Доставлено: {delivered}\n"
                        f"🚫 Заблокировали: {blocked}\n"
                        f"⚠️ Ошибок: {failed}"
                    ),
                    parse_mode="HTML",
                )
            except Exception:
                pass

        await asyncio.sleep(_RATE_DELAY_SEC)

    elapsed = time.monotonic() - started
    summary = (
        "📣 <b>Рассылка завершена</b>\n\n"
        f"📥 Всего: <b>{total}</b>\n"
        f"✅ Доставлено: <b>{delivered}</b>\n"
        f"🚫 Заблокировали бота: <b>{blocked}</b>\n"
        f"⚠️ Ошибок: <b>{failed}</b>\n"
        f"⏱ Время: <b>{elapsed:.1f} сек</b>"
    )
    try:
        await bot.send_message(admin_chat_id, summary, parse_mode="HTML")
    except Exception:
        logger.exception("[BROADCAST] failed to send summary to admin %s", admin_chat_id)
