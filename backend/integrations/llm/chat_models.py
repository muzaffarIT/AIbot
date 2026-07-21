"""Registry of available text-chat models.

Adding / removing a model is a one-line change here — the API, the miniapp
selector and credit charging all read from this list. Each model declares which
adapter transports it (see `kie_chat.py`) and how many credits a reply costs.

KIE enables/disables model slugs on their side over time; when a slug goes live
just flip `enabled=True` (or add it). If a slug is temporarily unavailable KIE
returns an error which we surface to the user without charging credits.
"""
from __future__ import annotations

from dataclasses import dataclass

from backend.core.config import settings


@dataclass(frozen=True, slots=True)
class ChatModel:
    id: str            # stable id used by the miniapp + stored on messages
    label: str         # human display name
    slug: str          # model slug sent to the provider
    adapter: str       # "kie_chat" | "kie_codex"
    cost: int          # credits charged per assistant reply
    group: str         # family, for grouping in the UI
    enabled: bool = True
    reasoning: bool = False   # exposes a "thinking" model
    description: str = ""


# Order matters — first enabled model is the default selection.
CHAT_MODELS: tuple[ChatModel, ...] = (
    # ── DeepSeek (confirmed live on KIE /chat/completions) ────────────────
    ChatModel(
        id="deepseek-chat", label="DeepSeek V3", slug="deepseek-chat",
        adapter="kie_chat", cost=1, group="DeepSeek",
        description="Быстрая универсальная модель для общения и текста.",
    ),
    ChatModel(
        id="deepseek-reasoner", label="DeepSeek R1 (reasoning)", slug="deepseek-reasoner",
        adapter="kie_chat", cost=2, group="DeepSeek", reasoning=True,
        description="Рассуждающая модель — сложные задачи, код, логика.",
    ),
    # ── OpenAI GPT-5.6 (KIE /codex/v1/responses) ──────────────────────────
    ChatModel(
        id="gpt-5-6-sol", label="ChatGPT 5.6 Sol", slug="gpt-5-6-sol",
        adapter="kie_codex", cost=3, group="ChatGPT",
        description="Флагман OpenAI — сильный в рассуждениях и коде.",
    ),
    ChatModel(
        id="gpt-5-6-luna", label="ChatGPT 5.6 Luna", slug="gpt-5-6-luna",
        adapter="kie_codex", cost=2, group="ChatGPT",
        description="Быстрый и сбалансированный вариант GPT-5.6.",
    ),
    # ── Google Gemini (documented on KIE) ─────────────────────────────────
    ChatModel(
        id="gemini-2-5-flash", label="Gemini 2.5 Flash", slug="gemini-2-5-flash",
        adapter="kie_chat", cost=1, group="Gemini",
        description="Быстрые ответы, длинный контекст.",
    ),
    ChatModel(
        id="gemini-2-5-pro", label="Gemini 2.5 Pro", slug="gemini-2-5-pro",
        adapter="kie_chat", cost=2, group="Gemini", reasoning=True,
        description="Продвинутые рассуждения для сложных промптов.",
    ),
    # ── Anthropic Claude (enable when the KIE slug is confirmed) ───────────
    ChatModel(
        id="claude-sonnet", label="Claude Sonnet", slug="claude-sonnet-4-5",
        adapter="kie_chat", cost=3, group="Claude", enabled=False,
        description="Лучшая модель для письма и кода (включим по готовности).",
    ),
)

_BY_ID: dict[str, ChatModel] = {m.id: m for m in CHAT_MODELS}


def _env_allowlist() -> set[str] | None:
    raw = (settings.chat_models_enabled or "").strip()
    if not raw:
        return None
    return {x.strip() for x in raw.split(",") if x.strip()}


def get_model(model_id: str) -> ChatModel | None:
    return _BY_ID.get(model_id)


def available_models() -> list[ChatModel]:
    """Models shown to users: registry `enabled` flags, optionally narrowed
    by the CHAT_MODELS_ENABLED env allow-list."""
    allow = _env_allowlist()
    out = []
    for m in CHAT_MODELS:
        if allow is not None:
            if m.id in allow:
                out.append(m)
        elif m.enabled:
            out.append(m)
    return out


def default_model_id() -> str | None:
    models = available_models()
    return models[0].id if models else None
