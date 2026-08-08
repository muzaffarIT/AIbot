"""
Showcase gallery — the #1 acquisition lever from Suzma's playbook.

Suzma grows almost entirely through Instagram Reels where they show a
finished "wow" generation and say "made with Suzma". That is show-don't-tell
marketing: the user sees what's possible before they ever write a prompt.

This module brings the same mechanic in-bot. Each showcase item is a
curated example (image URL + the exact prompt that made it + the model).
New users see it on /start; anyone can open it from the menu. Every item
has a "use this prompt" button — one tap drops the prompt into the
generation flow, so the path from inspiration → first generation is a
single click. That collapses the biggest drop-off for new AI-bot users
("I don't know what to write").
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass

from aiogram import F, Router, Bot
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.utils.media_group import MediaGroupBuilder

from bot.services.db_session import get_db_session
from backend.services.user_service import UserService
from shared.utils.i18n import I18n

logger = logging.getLogger(__name__)
router = Router()
i18n = I18n()


@dataclass(frozen=True, slots=True)
class ShowcaseItem:
    """A single curated example shown to inspire new users."""
    id: str
    prompt: str                # the exact English prompt that produced this
    image_url: str             # publicly reachable demo image
    caption_ru: str            # short hook in RU
    caption_uz: str            # short hook in UZ
    provider: str              # which model to route to ("nano" by default)


# NOTE on image URLs: these are placeholder demo URLs. Replace with real
# HARF AI generations (your own best outputs) hosted on a stable CDN /
# Telegram file_id before a big traffic push — self-hosted examples are
# both cheaper and immune to third-party link rot. The flow works with
# any https image URL, so swapping them is the only change needed.
SHOWCASE: tuple[ShowcaseItem, ...] = (
    ShowcaseItem(
        id="city",
        prompt=(
            "a futuristic city at night, neon lights reflecting on wet streets, "
            "flying cars, cinematic wide shot, 8k, hyperrealistic"
        ),
        image_url=(
            "https://images.unsplash.com/photo-1519046904884-53103b34b206?"
            "auto=format&fit=crop&w=1200&q=80"
        ),
        caption_ru="🌃 Киберпанк-город ночью — за 10 кредитов",
        caption_uz="🌃 Kiberpank shahar tuni — 10 kredit bilan",
        provider="nano",
    ),
    ShowcaseItem(
        id="portrait",
        prompt=(
            "cinematic portrait of a wise old man, dramatic side lighting, "
            "detailed skin texture, shallow depth of field, 85mm, photorealistic"
        ),
        image_url=(
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?"
            "auto=format&fit=crop&w=1200&q=80"
        ),
        caption_ru="📸 Кинематографичный портрет — за 10 кредитов",
        caption_uz="📸 Kinematografik portret — 10 kredit bilan",
        provider="nano",
    ),
    ShowcaseItem(
        id="fantasy",
        prompt=(
            "a majestic dragon flying over snowy mountains at sunrise, epic scale, "
            "volumetric light, fantasy concept art, ultra detailed"
        ),
        image_url=(
            "https://images.unsplash.com/photo-1518709268805-4e9042af2176?"
            "auto=format&fit=crop&w=1200&q=80"
        ),
        caption_ru="🐉 Дракон над горами — фантазия в 1 клик",
        caption_uz="🐉 Tog'lar ustida ajdaho — 1 ta bosishda fantaziya",
        provider="nano",
    ),
    ShowcaseItem(
        id="food",
        prompt=(
            "professional food photography of a gourmet burger, melted cheese, "
            "sesame bun, soft natural light, top-down, mouthwatering, 8k"
        ),
        image_url=(
            "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?"
            "auto=format&fit=crop&w=1200&q=80"
        ),
        caption_ru="🍔 Сочная еда для соцсетей — за 10 кредитов",
        caption_uz="🍔 Ijtimoiy tarmoq uchun shirin taom — 10 kredit bilan",
        provider="nano",
    ),
)


def _lang_of(telegram_id: int) -> str:
    db = get_db_session()
    try:
        user = UserService(db).get_user_by_telegram_id(telegram_id)
        return (user.language_code if user else None) or "ru"
    finally:
        db.close()


def _item_text(item: ShowcaseItem, lang: str) -> str:
    caption = item.caption_uz if lang == "uz" else item.caption_ru
    if lang == "uz":
        return (
            f"{caption}\n\n"
            f"📝 <b>Prompt:</b>\n<i>{item.prompt}</i>\n\n"
            f"👆 «Bu promptdan foydalanish» tugmasini bosing — men sizning "
            f"uchun yarataman!"
        )
    return (
        f"{caption}\n\n"
        f"📝 <b>Промпт:</b>\n<i>{item.prompt}</i>\n\n"
        f"👆 Нажмите «Использовать этот промпт» — я создам это для вас!"
    )


def _item_keyboard(item: ShowcaseItem, lang: str, idx: int, total: int) -> InlineKeyboardMarkup:
    use_text = "✨ Использовать промпт" if lang != "uz" else "✨ Promptdan foydalanish"
    next_text = "Следующий пример →" if lang != "uz" else "Keyingi misol →"
    menu_text = "🏠 Главное меню" if lang != "uz" else "🏠 Bosh menyu"

    rows = [
        [InlineKeyboardButton(text=use_text, callback_data=f"showcase_use:{item.id}")],
    ]
    # Navigation: only show "next" if there is one
    if idx < total - 1:
        rows.append([
            InlineKeyboardButton(text=next_text, callback_data=f"showcase:{item.id}"),
            InlineKeyboardButton(text=menu_text, callback_data="start_menu"),
        ])
    else:
        rows.append([InlineKeyboardButton(text=menu_text, callback_data="start_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _find(item_id: str) -> ShowcaseItem | None:
    for it in SHOWCASE:
        if it.id == item_id:
            return it
    return None


async def send_showcase(message_or_callback_message, telegram_id: int) -> None:
    """Show a random showcase item as the very first "wow" moment.

    Picks randomly so repeat /start visits don't feel stale. The user can
    swipe through the rest with the "next" button.
    """
    lang = _lang_of(telegram_id)
    item = random.choice(SHOWCASE)
    idx = SHOWCASE.index(item)
    try:
        await message_or_callback_message.answer_photo(
            photo=item.image_url,
            caption=_item_text(item, lang),
            reply_markup=_item_keyboard(item, lang, idx, len(SHOWCASE)),
            parse_mode="HTML",
        )
    except Exception as e:
        # Image hosts fail. Fall back to text-only so the flow still teaches
        # the user what a good prompt looks like.
        logger.warning(f"[Showcase] image send failed, fallback to text: {e}")
        await message_or_callback_message.answer(
            _item_text(item, lang),
            reply_markup=_item_keyboard(item, lang, idx, len(SHOWCASE)),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "menu_showcase")
async def showcase_open(callback: CallbackQuery) -> None:
    """Open the gallery from the main-menu button."""
    await send_showcase(callback.message, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("showcase:"))
async def showcase_next(callback: CallbackQuery) -> None:
    """Navigate to the next showcase item."""
    current_id = callback.data.split(":", 1)[1]
    lang = _lang_of(callback.from_user.id)

    # Find the NEXT item after the current one; wrap around if at the end.
    try:
        idx = next(i for i, it in enumerate(SHOWCASE) if it.id == current_id)
        nxt = SHOWCASE[(idx + 1) % len(SHOWCASE)]
    except StopIteration:
        nxt = SHOWCASE[0]
    new_idx = SHOWCASE.index(nxt)

    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=nxt.image_url,
                caption=_item_text(nxt, lang),
                parse_mode="HTML",
            ),
            reply_markup=_item_keyboard(nxt, lang, new_idx, len(SHOWCASE)),
        )
    except Exception as e:
        logger.warning(f"[Showcase] edit_media failed: {e}")
    await callback.answer()


@router.callback_query(F.data.startswith("showcase_use:"))
async def showcase_use(callback: CallbackQuery, bot: Bot) -> None:
    """Drop the showcase prompt straight into the Nano Banana flow.

    This is the single most important button: it removes the "I don't know
    what to write" barrier by handing the user a working prompt. We simulate
    the user typing it by reusing the existing Nano Banana entry point.
    """
    item_id = callback.data.split(":", 1)[1]
    item = _find(item_id)
    if not item:
        await callback.answer()
        return

    lang = _lang_of(callback.from_user.id)
    # Acknowledge, then open the create submenu so the user can pick the
    # model tier. The prompt itself is shown again as a reminder.
    if lang == "uz":
        ack = "✅ Prompt tayyor! Endi modelni tanlang 👇"
    else:
        ack = "✅ Промпт готов! Теперь выберите модель 👇"
    await callback.answer(ack, show_alert=True)

    from bot.keyboards.main_menu import create_submenu_keyboard
    reminder = (
        f"📝 <b>Tayyor prompt:</b>\n<i>{item.prompt}</i>\n\n"
        f"Endi modelni tanlang — keyin shu promptni yuboring."
        if lang == "uz" else
        f"📝 <b>Готовый промпт:</b>\n<i>{item.prompt}</i>\n\n"
        f"Теперь выберите модель — затем пришлите этот промпт."
    )
    await callback.message.answer(
        reminder,
        reply_markup=create_submenu_keyboard(lang),
        parse_mode="HTML",
    )
