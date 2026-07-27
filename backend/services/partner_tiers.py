"""Partner program tiers.

Referrals used to earn a flat 10%. Partners now level up: the more paying
referrals they bring, the higher their commission — the growth mechanic Syntx
uses. Tiers are derived (never stored), so they stay correct even if referral
rows are added or removed.

Only the commission RATE lives here; how money is actually moved is untouched
in payment_service.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PartnerTier:
    key: str
    name_ru: str
    name_uz: str
    emoji: str
    min_referrals: int   # paying referrals required to reach this tier
    rate: float          # commission share of each payment (0.10 = 10%)

    @property
    def percent(self) -> int:
        return round(self.rate * 100)


# Ordered from entry level up. First tier must start at 0.
PARTNER_TIERS: tuple[PartnerTier, ...] = (
    PartnerTier("bronze",   "Бронза",   "Bronza",  "🥉", 0,  0.10),
    PartnerTier("silver",   "Серебро",  "Kumush",  "🥈", 5,  0.13),
    PartnerTier("gold",     "Золото",   "Oltin",   "🥇", 15, 0.16),
    PartnerTier("platinum", "Платина",  "Platina", "💎", 40, 0.20),
    PartnerTier("legend",   "Легенда",  "Afsona",  "👑", 100, 0.25),
)

BASE_TIER = PARTNER_TIERS[0]


def tier_for(paid_referrals: int) -> PartnerTier:
    """Highest tier the partner qualifies for."""
    current = BASE_TIER
    for tier in PARTNER_TIERS:
        if paid_referrals >= tier.min_referrals:
            current = tier
        else:
            break
    return current


def next_tier(paid_referrals: int) -> PartnerTier | None:
    """The tier after the current one, or None at the top."""
    for tier in PARTNER_TIERS:
        if paid_referrals < tier.min_referrals:
            return tier
    return None


def commission_rate(paid_referrals: int) -> float:
    return tier_for(paid_referrals).rate


def serialize_tier(tier: PartnerTier, lang: str = "ru") -> dict:
    return {
        "key": tier.key,
        "name": tier.name_uz if lang == "uz" else tier.name_ru,
        "emoji": tier.emoji,
        "min_referrals": tier.min_referrals,
        "percent": tier.percent,
    }


def progress(paid_referrals: int, lang: str = "ru") -> dict:
    """Full partner standing for the API/UI."""
    current = tier_for(paid_referrals)
    nxt = next_tier(paid_referrals)
    return {
        "paid_referrals": paid_referrals,
        "current": serialize_tier(current, lang),
        "next": serialize_tier(nxt, lang) if nxt else None,
        "to_next": max(0, nxt.min_referrals - paid_referrals) if nxt else 0,
        "all_tiers": [serialize_tier(t, lang) for t in PARTNER_TIERS],
    }
