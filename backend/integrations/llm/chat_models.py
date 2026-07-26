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
    label: str         # human display name (proper noun — same in every language)
    slug: str          # model slug sent to the provider
    adapter: str       # "kie_chat" | "kie_codex"
    cost: int          # credits charged per assistant reply
    group: str         # family, for grouping in the UI
    enabled: bool = True
    reasoning: bool = False   # exposes a "thinking" model
    description: str = ""      # Russian description
    description_uz: str = ""   # Uzbek description


# Order matters — first enabled model is the default selection, so keep a
# currently-working model at the top. Live-status verified against KIE:
#   • gpt-5-6-luna / sol (codex endpoint) → WORKING
#   • deepseek-* (chat/completions)       → recognised, intermittently in
#     maintenance on KIE's side (kept enabled — comes back)
#   • gemini-* / claude-*                 → slug not yet enabled by KIE
#     ("Operation not found") → disabled until it goes live; flip enabled=True
CHAT_MODELS: tuple[ChatModel, ...] = (
    # ── OpenAI GPT-5.6 (KIE /codex/v1/responses) — verified working ───────
    ChatModel(
        id="gpt-5-6-luna", label="ChatGPT 5.6 Luna", slug="gpt-5-6-luna",
        adapter="kie_codex", cost=2, group="ChatGPT",
        description="Быстрый и сбалансированный. Отвечает на любые вопросы.",
        description_uz="Tez va muvozanatli. Har qanday savolga javob beradi.",
    ),
    ChatModel(
        id="gpt-5-6-sol", label="ChatGPT 5.6 Sol", slug="gpt-5-6-sol",
        adapter="kie_codex", cost=3, group="ChatGPT", reasoning=True,
        description="Флагман OpenAI — сильный в рассуждениях и коде.",
        description_uz="OpenAI flagmani — mulohaza va kodda kuchli.",
    ),
    ChatModel(
        id="gpt-5-6-terra", label="ChatGPT 5.6 Terra", slug="gpt-5-6-terra",
        adapter="kie_codex", cost=3, group="ChatGPT", reasoning=True,
        description="Мощный вариант GPT-5.6 для сложных задач.",
        description_uz="Murakkab vazifalar uchun kuchli GPT-5.6 varianti.",
    ),
    # ── DeepSeek (KIE /chat/completions) ──────────────────────────────────
    ChatModel(
        id="deepseek-chat", label="DeepSeek V3", slug="deepseek-chat",
        adapter="kie_chat", cost=1, group="DeepSeek",
        description="Быстрая универсальная модель для общения и текста.",
        description_uz="Muloqot va matn uchun tez universal model.",
    ),
    ChatModel(
        id="deepseek-reasoner", label="DeepSeek R1 (reasoning)", slug="deepseek-reasoner",
        adapter="kie_chat", cost=2, group="DeepSeek", reasoning=True,
        description="Рассуждающая модель — сложные задачи, код, логика.",
        description_uz="Mulohaza yurituvchi model — murakkab vazifa, kod, mantiq.",
    ),
    # ── Google Gemini (enable when KIE turns the slug on) ─────────────────
    ChatModel(
        id="gemini-2-5-flash", label="Gemini 2.5 Flash", slug="gemini-2-5-flash",
        adapter="kie_chat", cost=1, group="Gemini", enabled=False,
        description="Быстрые ответы, длинный контекст.",
        description_uz="Tez javoblar, uzun kontekst.",
    ),
    ChatModel(
        id="gemini-2-5-pro", label="Gemini 2.5 Pro", slug="gemini-2-5-pro",
        adapter="kie_chat", cost=2, group="Gemini", reasoning=True, enabled=False,
        description="Продвинутые рассуждения для сложных промптов.",
        description_uz="Murakkab promptlar uchun ilg'or mulohaza.",
    ),
    # ── Anthropic Claude (enable when the KIE slug is confirmed) ───────────
    ChatModel(
        id="claude-sonnet", label="Claude Sonnet", slug="claude-sonnet-4-5",
        adapter="kie_chat", cost=3, group="Claude", enabled=False,
        description="Лучшая модель для письма и кода (включим по готовности).",
        description_uz="Yozish va kod uchun eng yaxshi model (tayyor bo'lganda yoqamiz).",
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
