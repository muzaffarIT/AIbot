"""Partner program statistics.

A referral counts as "paid" once they have spent real money — either a
confirmed plan payment or a UZS top-up. That number drives the partner tier
(see partner_tiers.py).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def referral_spend_uzs(db: Session, referred_user_id: int) -> float:
    """Total real money a referred user has put in (payments + UZS top-ups)."""
    paid = db.execute(
        text(
            "SELECT COALESCE(SUM(p.amount), 0) AS total "
            "FROM payments p JOIN orders o ON p.order_id = o.id "
            "WHERE o.user_id = :uid AND p.status = 'paid'"
        ),
        {"uid": referred_user_id},
    ).scalar() or 0

    topup = db.execute(
        text(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM uzs_transactions "
            "WHERE user_id = :uid AND type = 'topup'"
        ),
        {"uid": referred_user_id},
    ).scalar() or 0

    return float(paid) + float(topup)


def count_paid_referrals(db: Session, referrer_telegram_id: int) -> int:
    """How many of this partner's referrals have paid at least once."""
    row = db.execute(
        text(
            "SELECT COUNT(*) FROM users u WHERE u.referred_by_telegram_id = :tid AND ("
            "  EXISTS (SELECT 1 FROM payments p JOIN orders o ON p.order_id = o.id "
            "          WHERE o.user_id = u.id AND p.status = 'paid')"
            "  OR EXISTS (SELECT 1 FROM uzs_transactions t "
            "             WHERE t.user_id = u.id AND t.type = 'topup')"
            ")"
        ),
        {"tid": referrer_telegram_id},
    ).scalar()
    return int(row or 0)
