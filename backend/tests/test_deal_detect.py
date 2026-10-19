from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.models import Deal
from app.services.deal_detect import OFFER_TTL_DAYS, _in_window, saving_from_debit


def deal(**kw):
    base = dict(discount_type="percent", discount_value=Decimal("20"), max_discount=None, min_spend=None,
                valid_from=None, valid_until=None, days_of_week=[], requires_card=False)
    return Deal(**{**base, **kw})


def test_percent_discount_is_worked_out_from_the_amount_debited():
    saved, bill = saving_from_debit(deal(), Decimal("2080"))  # 20% off a Rs. 2,600 bill
    assert (saved, bill) == (Decimal("520.00"), Decimal("2600.00"))


def test_cashback_was_paid_in_full_up_front():
    saved, bill = saving_from_debit(deal(discount_type="cashback", discount_value=Decimal("5")), Decimal("4000"))
    assert (saved, bill) == (Decimal("200.00"), Decimal("4000.00"))


def test_flat_discount_and_the_cap():
    assert saving_from_debit(deal(discount_type="flat", discount_value=Decimal("400")), Decimal("1100")) == (
        Decimal("400.00"), Decimal("1500.00"))
    saved, _ = saving_from_debit(deal(max_discount=Decimal("300")), Decimal("8000"))
    assert saved == Decimal("300.00")


def test_unknown_terms_claim_nothing():
    assert saving_from_debit(deal(discount_type="other"), Decimal("1000")) is None
    assert saving_from_debit(deal(discount_value=None), Decimal("1000")) is None
    assert saving_from_debit(deal(discount_value=Decimal("100")), Decimal("1000")) is None


def test_window_needs_the_offer_first_and_the_deal_dates():
    offered = datetime(2026, 10, 14, 9, tzinfo=UTC)  # a Wednesday
    d = deal(valid_until=date(2026, 10, 20))
    assert _in_window(d, offered, offered + timedelta(days=1))
    assert not _in_window(d, offered, offered - timedelta(hours=1))  # bought before being told
    assert not _in_window(d, offered, offered + timedelta(days=7))  # deal over
    assert not _in_window(deal(), offered, offered + timedelta(days=OFFER_TTL_DAYS + 1))  # offer went stale


def test_weekday_deals_only_count_on_those_days():
    offered = datetime(2026, 10, 12, 9, tzinfo=UTC)  # Monday
    friday = deal(days_of_week=[4])
    assert _in_window(friday, offered, datetime(2026, 10, 16, 15, tzinfo=UTC))
    assert not _in_window(friday, offered, datetime(2026, 10, 15, 15, tzinfo=UTC))
    # 20:30 UTC on Thursday is already Friday 01:30 in Pakistan
    assert _in_window(friday, offered, datetime(2026, 10, 15, 20, 30, tzinfo=UTC))
