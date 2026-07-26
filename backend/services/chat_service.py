"""Text-chat orchestration: credits → persistence → LLM → reply.

Charging mirrors generation: a per-model credit cost is deducted per assistant
reply (admins are free). Credits are only charged AFTER the model answers, so a
provider failure never costs the user anything.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.chat import ChatMessage, Conversation
from backend.services.balance_service import BalanceService
from backend.services.user_service import UserService
from backend.integrations.llm import chat_models
from backend.integrations.llm.kie_chat import KieChatClient, LLMError
from shared.enums.credit_transaction_type import CreditTransactionType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_RU = (
    "Ты — HARF AI, дружелюбный и полезный ассистент внутри Telegram. "
    "Отвечай ПО-РУССКИ, кратко и по делу, с markdown-разметкой где уместно. "
    "Если пользователь пишет на другом языке — отвечай на языке его сообщения."
)

SYSTEM_PROMPT_UZ = (
    "Sen — HARF AI, Telegram ichidagi do'stona va foydali yordamchisan. "
    "O'ZBEK TILIDA, qisqa va aniq javob ber, kerak joyda markdown ishlat. "
    "Agar foydalanuvchi boshqa tilda yozsa — o'sha til bilan javob ber."
)


def _system_prompt(lang: str | None) -> str:
    return SYSTEM_PROMPT_UZ if lang == "uz" else SYSTEM_PROMPT_RU


class ChatError(Exception):
    """User-safe error surfaced to the API layer."""


class ChatService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_service = UserService(db)
        self.balance_service = BalanceService(db)

    # ── reads ─────────────────────────────────────────────────────────────

    def list_models(self, lang: str = "ru") -> list[dict]:
        uz = lang == "uz"
        return [
            {
                "id": m.id,
                "label": m.label,
                "group": m.group,
                "cost": m.cost,
                "reasoning": m.reasoning,
                "description": (m.description_uz or m.description) if uz else m.description,
            }
            for m in chat_models.available_models()
        ]

    def get_conversations(self, telegram_user_id: int, limit: int = 30) -> list[dict]:
        user = self.user_service.get_user_by_telegram_id(telegram_user_id)
        if not user:
            return []
        rows = (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [self._conv_dict(c) for c in rows]

    def get_messages(self, telegram_user_id: int, conversation_id: int, limit: int = 100) -> list[dict]:
        user = self.user_service.get_user_by_telegram_id(telegram_user_id)
        if not user:
            raise ChatError("Пользователь не найден")
        conv = self._owned_conversation(conversation_id, user.id)
        if not conv:
            raise ChatError("Диалог не найден")
        rows = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conv.id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .all()
        )
        return [self._msg_dict(m) for m in rows]

    # ── main action ───────────────────────────────────────────────────────

    def send_message(
        self,
        *,
        telegram_user_id: int,
        model_id: str,
        text: str,
        conversation_id: int | None = None,
    ) -> dict:
        text = (text or "").strip()
        if not text:
            raise ChatError("Сообщение пустое")
        if len(text) > 4000:
            raise ChatError("Сообщение слишком длинное (макс. 4000 символов)")

        model = chat_models.get_model(model_id)
        if model is None or (model not in chat_models.available_models()):
            raise ChatError("Модель недоступна. Выберите другую.")

        user = self.user_service.get_user_by_telegram_id(telegram_user_id)
        if not user:
            raise ChatError("Пользователь не найден")

        is_admin = user.telegram_user_id in settings.admin_ids_list
        cost = 0 if is_admin else model.cost

        if not is_admin and cost > 0:
            balance = self.balance_service.get_balance_value(user.id)
            if balance < cost:
                raise ChatError("Недостаточно кредитов. Пополните баланс.")

        # Resolve / create the conversation
        conv = None
        if conversation_id is not None:
            conv = self._owned_conversation(conversation_id, user.id)
            if conv is None:
                raise ChatError("Диалог не найден")
        if conv is None:
            conv = Conversation(user_id=user.id, model_id=model.id, title=text[:60])
            self.db.add(conv)
            self.db.flush()  # assign id

        # Persist the user's message
        user_msg = ChatMessage(
            conversation_id=conv.id, user_id=user.id,
            role="user", content=text, model_id=model.id, credits_charged=0,
        )
        self.db.add(user_msg)
        self.db.flush()

        # Build context window and call the model
        history = self._build_context(conv.id, model_id=model.id, lang=user.language_code)
        try:
            client = KieChatClient()
            result = client.complete(model=model, messages=history)
        except LLMError as exc:
            # Roll the user message back so a failed turn leaves no orphan and
            # nothing is charged.
            self.db.rollback()
            raise ChatError(str(exc)) from exc

        # Persist assistant reply + charge credits
        assistant_msg = ChatMessage(
            conversation_id=conv.id, user_id=user.id,
            role="assistant", content=result.content, model_id=model.id,
            credits_charged=cost,
        )
        self.db.add(assistant_msg)
        conv.model_id = model.id
        self.db.flush()

        if cost > 0:
            try:
                self.balance_service.subtract_credits(
                    user_id=user.id,
                    amount=cost,
                    transaction_type=CreditTransactionType.WRITEOFF,
                    reference_type="chat_message",
                    reference_id=str(assistant_msg.id),
                    comment=f"Chat reply · {model.label}",
                )
            except Exception as exc:  # pragma: no cover — balance is source of truth
                logger.error("[CHAT] credit charge failed for user %s: %s", user.id, exc)

        self.db.commit()

        new_balance = self.balance_service.get_balance_value(user.id)
        return {
            "conversation_id": conv.id,
            "model_id": model.id,
            "reply": result.content,
            "credits_charged": cost,
            "credits_balance": new_balance,
            "message_id": assistant_msg.id,
        }

    # ── helpers ───────────────────────────────────────────────────────────

    def _owned_conversation(self, conversation_id: int, user_id: int) -> Conversation | None:
        return (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
            .first()
        )

    def _build_context(self, conversation_id: int, *, model_id: str, lang: str | None = None) -> list[dict[str, str]]:
        window = settings.chat_history_window
        rows = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(window)
            .all()
        )
        rows.reverse()  # chronological order
        messages: list[dict[str, str]] = [{"role": "system", "content": _system_prompt(lang)}]
        for m in rows:
            messages.append({"role": m.role, "content": m.content})
        return messages

    @staticmethod
    def _conv_dict(c: Conversation) -> dict:
        return {
            "id": c.id,
            "model_id": c.model_id,
            "title": c.title,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }

    @staticmethod
    def _msg_dict(m: ChatMessage) -> dict:
        return {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "model_id": m.model_id,
            "credits_charged": m.credits_charged,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
