"""KIE.ai text-chat client.

Two transports, one normalized result:

  • kie_chat  → POST /api/v1/chat/completions  (OpenAI chat-completions shape)
  • kie_codex → POST /codex/v1/responses       (OpenAI "responses" shape)

Both are wrapped so callers just get a `ChatResult(content, usage, raw)` and a
single `LLMError` on failure. Response parsing is intentionally defensive: KIE
sometimes returns the raw OpenAI object and sometimes wraps it in
`{code, msg, data}`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from backend.core.config import settings
from backend.integrations.llm.chat_models import ChatModel


class LLMError(RuntimeError):
    """Raised when the provider fails. Message is safe to show the user."""


@dataclass(slots=True)
class ChatResult:
    content: str
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class KieChatClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 90.0,
    ) -> None:
        self.api_key = api_key or settings.kie_api_key
        self.base_url = (base_url or settings.kie_base_url or "https://api.kie.ai").rstrip("/")
        self.timeout_seconds = timeout_seconds

    # ── public API ────────────────────────────────────────────────────────

    def complete(self, *, model: ChatModel, messages: list[dict[str, str]]) -> ChatResult:
        """Send a conversation and return the assistant reply.

        `messages` is a list of {"role": "user"|"assistant"|"system",
        "content": str}.
        """
        if not self.api_key:
            raise LLMError("Сервис ИИ временно недоступен (нет ключа).")

        if model.adapter == "kie_codex":
            return self._codex_responses(model, messages)
        return self._chat_completions(model, messages)

    # ── transports ────────────────────────────────────────────────────────

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                resp = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise LLMError("Не удалось связаться с сервисом ИИ. Попробуйте ещё раз.") from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMError("Некорректный ответ от сервиса ИИ.") from exc

        # KIE error envelope: {"code": 4xx/5xx, "msg": "...", "data": null}
        code = data.get("code")
        if isinstance(code, int) and code not in (0, 200):
            raise LLMError(_friendly_kie_error(data.get("msg")))
        if resp.status_code >= 400 and code is None:
            raise LLMError(_friendly_kie_error(data.get("message") or data.get("error")))
        return data

    def _chat_completions(self, model: ChatModel, messages: list[dict[str, str]]) -> ChatResult:
        payload = {
            "model": model.slug,
            "messages": messages,
            "max_tokens": settings.chat_max_tokens,
            "stream": False,
        }
        data = self._post(settings.kie_chat_path, payload)
        content = _extract_chat_content(data)
        if not content:
            raise LLMError("Модель вернула пустой ответ. Попробуйте переформулировать.")
        return ChatResult(content=content, usage=_extract_usage(data), raw=data)

    def _codex_responses(self, model: ChatModel, messages: list[dict[str, str]]) -> ChatResult:
        payload = {
            "model": model.slug,
            "input": [_to_responses_item(m) for m in messages],
            "stream": False,
        }
        data = self._post(settings.kie_codex_path, payload)
        content = _extract_responses_content(data)
        if not content:
            raise LLMError("Модель вернула пустой ответ. Попробуйте переформулировать.")
        return ChatResult(content=content, usage=_extract_usage(data), raw=data)


# ── parsing helpers ──────────────────────────────────────────────────────────

def _unwrap(data: dict[str, Any]) -> dict[str, Any]:
    """KIE may wrap the real payload under `data`."""
    inner = data.get("data")
    if isinstance(inner, dict):
        return inner
    return data


def _extract_chat_content(data: dict[str, Any]) -> str:
    d = _unwrap(data)
    choices = d.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            return content.strip()
        # some providers return content as a list of parts
        if isinstance(content, list):
            return "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            ).strip()
    # last-ditch: a bare "content" / "text"
    for key in ("content", "text", "output_text"):
        val = d.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _extract_responses_content(data: dict[str, Any]) -> str:
    d = _unwrap(data)
    # OpenAI Responses API: convenience field first
    if isinstance(d.get("output_text"), str) and d["output_text"].strip():
        return d["output_text"].strip()
    output = d.get("output")
    parts: list[str] = []
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and isinstance(c.get("text"), str):
                        parts.append(c["text"])
            elif isinstance(content, str):
                parts.append(content)
    if parts:
        return "".join(parts).strip()
    # fall back to chat-style parsing just in case
    return _extract_chat_content(data)


def _extract_usage(data: dict[str, Any]) -> dict[str, Any]:
    d = _unwrap(data)
    usage = d.get("usage")
    return usage if isinstance(usage, dict) else {}


def _to_responses_item(message: dict[str, str]) -> dict[str, Any]:
    role = message.get("role", "user")
    text = message.get("content", "")
    part_type = "output_text" if role == "assistant" else "input_text"
    return {"role": role, "content": [{"type": part_type, "text": text}]}


def _friendly_kie_error(msg: str | None) -> str:
    raw = (msg or "").strip()
    low = raw.lower()
    if "operation not found" in low or "not supported" in low:
        return "Эта модель сейчас недоступна. Выберите другую."
    if "maintained" in low or "maintenance" in low:
        return "Модель на техобслуживании. Попробуйте позже или выберите другую."
    if "insufficient" in low or "credit" in low or "balance" in low:
        return "Сервис ИИ временно недоступен (лимит провайдера)."
    return raw or "Сервис ИИ вернул ошибку. Попробуйте ещё раз."
