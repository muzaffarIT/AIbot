"""Voice-message AI chat.

A voice message → speech-to-text (KIE) → answer via the shared ChatService
(same models/credits as the mini-app chat) → text reply (and an optional
spoken reply when TTS is available).

Uses Telegram's own file URL as the audio source, so there's no browser
recording / upload / codec handling. Gated by settings.voice_enabled and
degrades gracefully if the voice provider is down — the user is told to type
instead, nothing crashes.

This handler is global (F.voice) and does not collide with the text FSM
prompt handlers, which only match F.text.
"""
import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.types import Message

from backend.core.config import settings
from backend.integrations.llm import chat_models
from backend.integrations.voice.kie_voice import KieVoiceClient, VoiceError
from backend.services.chat_service import ChatError, ChatService
from bot.services.db_session import get_db_session

logger = logging.getLogger(__name__)
router = Router()


def _transcribe(audio_url: str, lang: str | None) -> str:
    return KieVoiceClient().transcribe(audio_url, language_code=lang)


def _chat_reply(telegram_user_id: int, model_id: str, text: str) -> dict:
    db = get_db_session()
    try:
        return ChatService(db).send_message(
            telegram_user_id=telegram_user_id, model_id=model_id, text=text
        )
    finally:
        db.close()


def _synthesize(text: str) -> str:
    return KieVoiceClient().synthesize(text)


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot) -> None:
    if not settings.voice_enabled:
        return

    model_id = chat_models.default_model_id()
    if not model_id:
        await message.answer("💬 Чат временно недоступен.")
        return

    file = await bot.get_file(message.voice.file_id)
    audio_url = f"https://api.telegram.org/file/bot{settings.bot_token}/{file.file_path}"

    status = await message.answer("🎤 Слушаю…")

    # 1. Speech → text (blocking → thread so the bot loop stays free)
    try:
        transcript = await asyncio.to_thread(_transcribe, audio_url, None)
    except VoiceError as exc:
        await status.edit_text(f"🎤 {exc}\nНапиши текстом — отвечу сразу.")
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("[VOICE] transcribe failed: %s", exc)
        await status.edit_text("🎤 Не удалось распознать голос. Напиши текстом.")
        return

    if not transcript.strip():
        await status.edit_text("🎤 Не расслышал 🙈 Скажи ещё раз или напиши текстом.")
        return

    await status.edit_text(f"🎤 <i>«{transcript}»</i>\n\n⏳ Думаю…", parse_mode="HTML")

    # 2. Answer via the shared chat engine
    try:
        result = await asyncio.to_thread(_chat_reply, message.from_user.id, model_id, transcript)
    except ChatError as exc:
        await status.edit_text(f"🎤 <i>«{transcript}»</i>\n\n❌ {exc}", parse_mode="HTML")
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("[VOICE] chat failed: %s", exc)
        await status.edit_text("❌ Ошибка. Попробуй ещё раз.")
        return

    reply = result.get("reply") or "…"
    await status.edit_text(f"🎤 <i>«{transcript}»</i>\n\n{reply}", parse_mode="HTML")

    # 3. Optional spoken reply
    if settings.voice_reply_with_audio:
        try:
            audio_url_out = await asyncio.to_thread(_synthesize, reply[:1000])
            await message.answer_voice(audio_url_out)
        except Exception as exc:  # noqa: BLE001 — best effort
            logger.info("[VOICE] TTS reply skipped: %s", exc)
