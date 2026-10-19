"""Matching what a person says about their card to the catalog of cards banks actually issue."""

from dataclasses import dataclass

from app.models import CardProduct

# Rough order of card tiers, low to high, so "silver" can be matched to its nearest real tier ("classic", "gold").
TIER_LADDER = ["basic", "standard", "classic", "silver", "green", "gold", "titanium", "platinum", "premium",
               "signature", "world", "prestige", "infinite", "metal"]


@dataclass
class CardMatch:
    product: CardProduct | None  # the one card it can only be; None when unsure
    options: list[CardProduct]  # several fit equally well: ask which (no tier given)
    closest: list[CardProduct]  # nothing fits: "did you mean ...?", best first


def _tier_distance(a: str | None, b: str | None) -> int:
    if (a or "") == (b or ""):
        return 0
    if a in TIER_LADDER and b in TIER_LADDER:
        return abs(TIER_LADDER.index(a) - TIER_LADDER.index(b))
    return len(TIER_LADDER)  # kids, virtual, unknown ...: far from everything


def match_card(products: list[CardProduct], network: str, card_type: str, tier: str | None) -> CardMatch:
    tier = (tier or "").strip().lower() or None
    fits = [p for p in products if p.card_type == card_type and p.network in (None, network)]
    if tier:
        exact = [p for p in fits if (p.tier or "") == tier or tier in p.name.lower().split()]
    else:
        exact = fits
    if len(exact) == 1:
        return CardMatch(exact[0], [], [])
    if len(exact) > 1:  # no tier given and the bank has several such cards: ask which one
        return CardMatch(None, exact, [])
    ranked = sorted(products, key=lambda p: (p.card_type != card_type, p.network not in (None, network),
                                             _tier_distance(p.tier, tier), p.name))
    return CardMatch(None, [], ranked[:3])
