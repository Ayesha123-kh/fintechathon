"""Notice that a person used a deal they were told about, from their spending alone.

When the assistant recommends a deal it records an offer (`record_offer`). Every new debit transaction is then
checked (`detect_redemption`): if it is at the deal's merchant, after the offer, inside the deal's dates and
weekdays, on a card the deal accepts and big enough for the minimum spend, the deal counts as used. The saving
is worked out from the amount actually debited, moved to the person's savings and announced in the chat.

Conservative on purpose: when the bank, the card or the amount cannot be established, nothing is claimed and
the person can still tell the assistant (`avail_deal`).
"""

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BankAccount, Card, Deal, DealOffer, DealRedemption, Merchant, Transaction
from app.services.deals import card_matches

log = logging.getLogger(__name__)

PKT = ZoneInfo("Asia/Karachi")
OFFER_TTL_DAYS = 14  # an offer without a tighter deal window counts for this long
CENT = Decimal("0.01")


def _money(x) -> Decimal:
    return Decimal(str(x or 0)).quantize(CENT)


def saving_from_debit(deal: Deal, debited: Decimal) -> tuple[Decimal, Decimal] | None:
    """(saved, bill before the discount) for a debit of `debited`, or None if the terms don't allow a figure.

    Instant discounts (percent, flat, bogo) are already off the amount the bank debited, so the bill was higher;
    cashback is paid back later, so the full bill was debited.
    """
    value = Decimal(str(deal.discount_value)) if deal.discount_value is not None else None
    cap = Decimal(str(deal.max_discount)) if deal.max_discount else None
    if debited <= 0:
        return None
    if deal.discount_type == "percent" and value and 0 < value < 100:
        rate = value / 100
        saved = debited * rate / (1 - rate)
    elif deal.discount_type == "flat" and value and value > 0:
        saved = value
    elif deal.discount_type == "cashback" and value and value > 0:
        saved = debited * value / 100
    elif deal.discount_type == "bogo":
        saved = debited  # paid for one, got the other free
    else:
        return None
    if cap:
        saved = min(saved, cap)
    saved = _money(saved)
    bill = _money(debited if deal.discount_type == "cashback" else debited + saved)
    return saved, bill


def _in_window(deal: Deal, offered_at: datetime, when: datetime) -> bool:
    if when < offered_at or when > offered_at + timedelta(days=OFFER_TTL_DAYS):
        return False
    local: date = when.astimezone(PKT).date()
    if deal.valid_from and local < deal.valid_from:
        return False
    if deal.valid_until and local > deal.valid_until:
        return False
    if deal.days_of_week and local.weekday() not in deal.days_of_week:
        return False
    return True


async def _eligible_card_label(s: AsyncSession, deal: Deal, tx: Transaction) -> str | None | bool:
    """True when no card is needed; the card's label when one qualifies; None when we can't tell."""
    if not deal.requires_card:
        return True
    if deal.card_type == "credit" or not tx.account_id:
        return None  # a bank alert doesn't say which card paid, so a credit-card deal can't be confirmed
    account = await s.get(BankAccount, tx.account_id)
    if not account or (deal.bank_id and account.bank_id != deal.bank_id):
        return None
    cards = (await s.execute(select(Card).where(Card.bank_id == account.bank_id))).scalars()
    for card in cards:
        if card_matches(deal, card):
            return card.label
    return None


async def record_offer(s: AsyncSession, user_id: uuid.UUID, deal_id: uuid.UUID) -> DealOffer:
    """The assistant told this person about the deal. Keeps the first open offer so its start doesn't move."""
    open_offer = await s.scalar(select(DealOffer).where(
        DealOffer.user_id == user_id, DealOffer.deal_id == deal_id, DealOffer.status == "open"))
    if open_offer:
        return open_offer
    offer = DealOffer(user_id=user_id, deal_id=deal_id)
    s.add(offer)
    await s.flush()
    return offer


async def detect_redemption(s: AsyncSession, user_id: uuid.UUID, tx: Transaction) -> DealRedemption | None:
    """Count a deal as used if this debit fits one the person was told about. Returns the redemption, if any."""
    if tx.direction != "debit" or not tx.merchant_id or tx.is_income:
        return None
    if await s.scalar(select(DealRedemption.id).where(DealRedemption.transaction_id == tx.id)):
        return None
    when = tx.occurred_at if tx.occurred_at.tzinfo else tx.occurred_at.replace(tzinfo=UTC)
    rows = (await s.execute(
        select(DealOffer, Deal).join(Deal, Deal.id == DealOffer.deal_id)
        .where(DealOffer.status == "open", Deal.merchant_id == tx.merchant_id, Deal.status != "rejected")
    )).all()
    best: tuple[Decimal, Decimal, DealOffer, Deal, str | None] | None = None
    for offer, deal in rows:
        if not _in_window(deal, offer.offered_at, when):
            continue
        card = await _eligible_card_label(s, deal, tx)
        if card is None:
            continue
        figures = saving_from_debit(deal, _money(tx.amount))
        if not figures:
            continue
        saved, bill = figures
        if saved <= 0 or (deal.min_spend and bill < _money(deal.min_spend)):
            continue
        if best is None or saved > best[0]:
            best = (saved, bill, offer, deal, None if card is True else card)
    if not best:
        return None

    from app.services import finance  # local import: finance calls this module
    from app.services.notify import notify

    saved, bill, offer, deal, card_label = best
    redemption = await finance.redeem_deal(s, user_id, bill, saved, deal_id=deal.id, transaction_id=tx.id)
    offer.status, offer.redeemed_at = "redeemed", datetime.now(UTC)
    merchant = await s.get(Merchant, tx.merchant_id)
    where = merchant.name if merchant else deal.merchant_name
    via = f" with your {card_label}" if card_label else ""
    import asyncio

    asyncio.get_running_loop().create_task(notify(
        user_id, "motivation", f"Great, you just saved Rs. {float(saved):,.0f}! 🎉",
        f"“{deal.title}” at {where}{via} saved you about Rs. {float(saved):,.0f}, and it has been moved to "
        "your savings.", url="/dashboard?chat=1",
    ))
    log.info("deal %s redeemed for user %s on transaction %s: Rs. %s", deal.id, user_id, tx.id, saved)
    return redemption
