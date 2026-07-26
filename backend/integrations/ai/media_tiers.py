"""Canonical image/video generation tiers.

Single source of truth for the mini app (and API) so a `quality_key` always
maps to the right provider, credit cost and worker payload. Mirrors the bot's
`bot/keyboards/quality_menu.QUALITY_DATA` — keep the two in sync (costs here are
the ones users are actually charged).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class MediaTier:
    key: str                 # e.g. "nano:hd" — the quality_key sent to /api/jobs
    label: str               # display name
    kind: str                # "image" | "video"
    provider: str            # AIProvider value: nano_banana | gpt_image | veo | kling
    cost: int                # credits charged
    emoji: str = ""
    note: str = ""           # short helper text, Russian (resolution / duration)
    note_uz: str = ""        # same helper text in Uzbek
    payload: dict[str, Any] = field(default_factory=dict)


# Order = display order within each kind. First image + first video are defaults.
MEDIA_TIERS: tuple[MediaTier, ...] = (
    # ── Images ────────────────────────────────────────────────────────────
    # Cheapest entry tier — verified working on KIE (0.8 provider credits).
    MediaTier(
        key="zimg:std", label="Z-Image", kind="image", provider="kie_image",
        cost=5, emoji="⚡", note="быстро · дёшево", note_uz="tez · arzon",
        payload={"_kie_model": "z-image", "image_size": "1:1", "aspect_ratio": "1:1"},
    ),
    MediaTier(
        key="nano:std", label="Nano Banana", kind="image", provider="nano_banana",
        cost=10, emoji="🍌", note="1K · быстро", note_uz="1K · tez",
        payload={"image_size": "1:1", "_nano_model": "nano-banana"},
    ),
    MediaTier(
        key="nano:hd", label="Nano Banana 2", kind="image", provider="nano_banana",
        cost=20, emoji="✨", note="2K", note_uz="2K",
        payload={"image_size": "1:1", "_nano_model": "nano-banana-2", "image_resolution": "2K"},
    ),
    MediaTier(
        key="nano:pro_hd", label="Nano Banana Pro", kind="image", provider="nano_banana",
        cost=30, emoji="⭐", note="2K · Pro", note_uz="2K · Pro",
        payload={"image_size": "1:1", "_nano_model": "nano-banana-pro", "image_resolution": "2K"},
    ),
    MediaTier(
        key="nano:4k", label="Nano Banana Pro 4K", kind="image", provider="nano_banana",
        cost=50, emoji="👑", note="4K", note_uz="4K",
        payload={"image_size": "1:1", "_nano_model": "nano-banana-pro", "image_resolution": "4K"},
    ),
    MediaTier(
        key="gpt:std", label="GPT Image 2", kind="image", provider="gpt_image",
        cost=30, emoji="🎨", note="OpenAI", note_uz="OpenAI",
        payload={"_gpt_model": "gpt-image-2"},
    ),
    # ── Video ─────────────────────────────────────────────────────────────
    MediaTier(
        key="veo:fast", label="Veo 3 Fast", kind="video", provider="veo",
        cost=30, emoji="🎬", note="быстрое видео", note_uz="tez video",
        payload={"model": "veo3_fast"},
    ),
    MediaTier(
        key="veo:quality", label="Veo 3 Quality", kind="video", provider="veo",
        cost=80, emoji="🎬", note="1080p", note_uz="1080p",
        payload={"model": "veo3_quality"},
    ),
    MediaTier(
        key="veo:4k", label="Veo 3 · 4K", kind="video", provider="veo",
        cost=90, emoji="🎬", note="4K апскейл", note_uz="4K apskeyl",
        payload={"model": "veo3_fast", "upscale_4k": True},
    ),
    MediaTier(
        key="kling:std5", label="Kling · 5с", kind="video", provider="kling",
        cost=40, emoji="🎥", note="5 сек", note_uz="5 soniya",
        payload={"mode": "std", "duration": "5"},
    ),
    MediaTier(
        key="kling:pro5", label="Kling Pro · 5с", kind="video", provider="kling",
        cost=70, emoji="🎥", note="5 сек · Pro", note_uz="5 soniya · Pro",
        payload={"mode": "pro", "duration": "5"},
    ),
    MediaTier(
        key="kling:pro10", label="Kling Pro · 10с", kind="video", provider="kling",
        cost=120, emoji="🎥", note="10 сек · Pro", note_uz="10 soniya · Pro",
        payload={"mode": "pro", "duration": "10"},
    ),
)

_BY_KEY: dict[str, MediaTier] = {t.key: t for t in MEDIA_TIERS}


def get_tier(key: str) -> MediaTier | None:
    return _BY_KEY.get(key)


def tiers_by_kind(lang: str = "ru") -> dict[str, list[dict]]:
    """Grouped, serializable tier list for the API/UI, localized to `lang`."""
    uz = lang == "uz"
    out: dict[str, list[dict]] = {"image": [], "video": []}
    for t in MEDIA_TIERS:
        out.setdefault(t.kind, []).append(
            {
                "key": t.key,
                "label": t.label,
                "kind": t.kind,
                "provider": t.provider,
                "cost": t.cost,
                "emoji": t.emoji,
                "note": (t.note_uz or t.note) if uz else t.note,
            }
        )
    return out
