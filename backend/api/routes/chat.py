from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.services.chat_service import ChatError, ChatService

router = APIRouter()


class SendMessageRequest(BaseModel):
    # `model_id` would otherwise collide with pydantic's protected `model_` namespace
    model_config = ConfigDict(protected_namespaces=())

    telegram_user_id: int
    model_id: str
    message: str
    conversation_id: int | None = None


@router.get("/models")
def list_models(lang: str = Query(default="ru"), db: Session = Depends(get_db)) -> dict:
    try:
        return {"models": ChatService(db).list_models(lang)}
    finally:
        db.close()


@router.get("/conversations/{telegram_user_id}")
def list_conversations(
    telegram_user_id: int,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return {"conversations": ChatService(db).get_conversations(telegram_user_id, limit=limit)}
    finally:
        db.close()


@router.get("/conversations/{telegram_user_id}/{conversation_id}/messages")
def get_messages(
    telegram_user_id: int,
    conversation_id: int,
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    try:
        messages = ChatService(db).get_messages(telegram_user_id, conversation_id, limit=limit)
        return {"conversation_id": conversation_id, "messages": messages}
    except ChatError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    finally:
        db.close()


class TranscribeRequest(BaseModel):
    audio_url: str
    lang: str | None = None


@router.post("/transcribe")
def transcribe(payload: TranscribeRequest) -> dict:
    """Speech → text for the mini-app microphone."""
    from backend.core.config import settings
    from backend.integrations.voice.kie_voice import KieVoiceClient, VoiceError

    if not settings.voice_enabled:
        raise HTTPException(status_code=503, detail="Голос временно отключён.")
    try:
        text = KieVoiceClient().transcribe(payload.audio_url, language_code=payload.lang)
    except VoiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    if not text.strip():
        raise HTTPException(status_code=422, detail="Не удалось распознать речь.")
    return {"text": text}


@router.post("/send")
def send_message(payload: SendMessageRequest, db: Session = Depends(get_db)) -> dict:
    try:
        return ChatService(db).send_message(
            telegram_user_id=payload.telegram_user_id,
            model_id=payload.model_id,
            text=payload.message,
            conversation_id=payload.conversation_id,
        )
    except ChatError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    finally:
        db.close()
