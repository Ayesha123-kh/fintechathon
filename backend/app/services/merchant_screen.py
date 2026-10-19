"""Keep private payees away from the shared deal bots.

The merchant directory is global and filled from users' transactions, and the Deals Source Scout / Crawler
(which may run on a third-party LLM) read it. So every new merchant is first judged by the self-hosted model:
a business that could offer deals goes on to 'pending'; a private person ("Ali Khan", "Rent - Landlord")
becomes 'personal' and is never shown to the deal bots. If the model is unreachable the merchant waits in
'screening' (fail closed) and is judged again later.
"""

import logging

from sqlalchemy import select

from app.core.db import system_session
from app.core.llm import complete_json
from app.models import Merchant

log = logging.getLogger(__name__)

PENDING = "pending"  # a business: the Source Scout may look for its website and socials
SCREENING = "screening"  # not judged yet (model offline): hidden from the deal bots
PERSONAL = "personal"  # a private person or personal transfer: hidden from the deal bots for good
MIN_CONFIDENCE = 0.6

SYSTEM = (
    "You screen payees from Pakistani bank alerts for a budgeting app. Decide whether the payee is a BUSINESS "
    "that could run public discounts or deals (restaurant, shop, brand, online store, pharmacy, fuel station, "
    "cinema, telecom, bill company ...) or a PERSON / personal transfer (a person's name, a family member, "
    "a landlord, a friend, 'Transfer to <name>', 'Raast from <name>', an account holder, a personal wallet). "
    'Reply as JSON: {"kind": "business" or "person", "confidence": number from 0 to 1}. '
    'Examples: "Transfer to Ali Khan" -> person. "Debited at Kababjees" -> business. "Sara Ahmed" -> person. '
    '"Imtiaz Super Market" -> business. "Rent - Landlord" -> person. "Foodpanda" -> business.'
)


async def classify_payee(name: str, description: str = "") -> bool | None:
    """True for a business, False for a person, None when the model could not be asked."""
    result = await complete_json(SYSTEM, f"Payee: {name}\nBank alert details: {description[:200]}", max_tokens=60)
    if not result:
        return None
    try:
        confidence = float(result.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
    return str(result.get("kind", "")).lower() == "business" and confidence >= MIN_CONFIDENCE


def status_for(is_business: bool | None) -> str:
    return SCREENING if is_business is None else PENDING if is_business else PERSONAL


async def screen_pending_merchants(limit: int = 50) -> int:
    """Judge merchants that were waiting for the model. Returns how many were decided."""
    async with system_session() as s:
        rows = (await s.execute(select(Merchant).where(Merchant.sources_status == SCREENING)
                                .order_by(Merchant.seen_in_transactions.desc()).limit(limit))).scalars().all()
        decided = 0
        for m in rows:
            verdict = await classify_payee(m.name)
            if verdict is None:
                break  # model still offline; try again next time
            m.sources_status = status_for(verdict)
            decided += 1
    if decided:
        log.info("screened %d merchants", decided)
    return decided
