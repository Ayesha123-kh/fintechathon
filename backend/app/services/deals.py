"""Matching deals to a user's cards, city and spending habits."""

import hashlib
import uuid
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.models import Bank, Card, Deal, Merchant, Transaction, UserProfile
from app.services.text import normalize_name


def deal_fingerprint(merchant: str, title: str, bank: str | None, valid_until: date | None) -> str:
    raw = f"{normalize_name(merchant)}|{title.lower().strip()}|{(bank or '').lower()}|{valid_until or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def card_matches(deal: Deal, card: Card) -> bool:
    if deal.bank_id and deal.bank_id != card.bank_id:
        return False
    if deal.card_network and deal.card_network.lower() != card.network.lower():
        return False
    if deal.card_type and deal.card_type.lower() != card.card_type.lower():
        return False
    if deal.card_tier and (card.tier or "").lower() != deal.card_tier.lower():
        return False
    return True


async def find_deals(
    s: AsyncSession,
    user_id: uuid.UUID,
    *,
    category: str | None = None,
    merchant: str | None = None,
    query: str | None = None,
    only_eligible: bool = True,
    limit: int = 15,
) -> list[dict]:
    today = clock.today()
    cards = list((await s.execute(select(Card))).scalars())
    profile = await s.get(UserProfile, user_id)
    city = (profile.city or "").lower() if profile else ""

    stmt = (
        select(Deal, Bank.name)
        .outerjoin(Bank, Bank.id == Deal.bank_id)
        .where(Deal.status == "active")
        .where(or_(Deal.valid_until.is_(None), Deal.valid_until >= today))
        .where(or_(Deal.valid_from.is_(None), Deal.valid_from <= today))
    )
    if category:
        stmt = stmt.where(Deal.category_slug == category)
    if merchant:
        stmt = stmt.where(Deal.merchant_name.ilike(f"%{merchant}%"))
    if query:
        like = f"%{query}%"
        stmt = stmt.where(or_(Deal.title.ilike(like), Deal.merchant_name.ilike(like), Deal.deal_type.ilike(like),
                              Deal.description.ilike(like)))
    # Prefer the merchants this user actually spends at.
    favourite = (
        select(Transaction.merchant_id, func.count().label("n"))
        .where(Transaction.merchant_id.is_not(None)).group_by(Transaction.merchant_id).subquery()
    )
    stmt = stmt.outerjoin(favourite, favourite.c.merchant_id == Deal.merchant_id).order_by(
        func.coalesce(favourite.c.n, 0).desc(), Deal.discount_value.desc().nulls_last()
    ).limit(200)

    out = []
    for deal, bank_name in (await s.execute(stmt)).all():
        if deal.cities and city and city not in [c.lower() for c in deal.cities]:
            continue
        if deal.days_of_week and today.weekday() not in deal.days_of_week:
            continue
        eligible_cards = [c.label for c in cards if card_matches(deal, c)] if deal.requires_card else []
        eligible = (not deal.requires_card) or bool(eligible_cards)
        if only_eligible and not eligible:
            continue
        out.append({
            "id": str(deal.id), "merchant": deal.merchant_name, "title": deal.title,
            "description": deal.description, "discount_type": deal.discount_type,
            "discount_value": float(deal.discount_value) if deal.discount_value is not None else None,
            "max_discount": float(deal.max_discount) if deal.max_discount is not None else None,
            "min_spend": float(deal.min_spend) if deal.min_spend is not None else None,
            "category": deal.category_slug, "deal_type": deal.deal_type,
            "requires_card": deal.requires_card, "bank": bank_name, "card_network": deal.card_network,
            "card_tier": deal.card_tier, "card_type": deal.card_type, "your_eligible_cards": eligible_cards,
            "valid_until": deal.valid_until.isoformat() if deal.valid_until else None,
            "days_of_week": deal.days_of_week, "cities": deal.cities, "source_url": deal.source_url,
        })
        if len(out) >= limit:
            break
    return out


async def estimate_saving(deal: Deal, amount: float) -> float:
    if deal.min_spend and amount < float(deal.min_spend):
        return 0.0
    value = float(deal.discount_value or 0)
    if deal.discount_type in ("percent", "cashback"):
        saving = amount * value / 100
    elif deal.discount_type == "flat":
        saving = value
    elif deal.discount_type == "bogo":
        saving = amount / 2
    else:
        saving = 0.0
    if deal.max_discount:
        saving = min(saving, float(deal.max_discount))
    return round(saving, 2)


async def merchants_for_crawl(s: AsyncSession, limit: int = 10) -> list[Merchant]:
    return list((await s.execute(
        select(Merchant).where(Merchant.sources_status == "ready")
        .order_by(Merchant.last_crawled_at.nulls_first(), Merchant.seen_in_transactions.desc()).limit(limit)
    )).scalars())
