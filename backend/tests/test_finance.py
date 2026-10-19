import uuid
from datetime import date
from decimal import Decimal

from app.models import Goal
from app.services.finance import split_savings
from app.services.gmail import regex_parse
from app.services.text import normalize_name


def goal(name, target, saved=0, deadline=None, priority=3, weight=None):
    return Goal(id=uuid.uuid4(), name=name, target_amount=Decimal(target), saved_amount=Decimal(saved),
                deadline=deadline, priority=priority, weight=weight, status="active")


def total(allocs):
    return sum(a.amount for a in allocs)


def test_equal_split_conserves_money():
    allocs = split_savings(Decimal("1000"), [goal("A", 10000), goal("B", 10000), goal("C", 10000)], "equal")
    assert total(allocs) == Decimal("1000.00")
    assert all(a.goal_id for a in allocs)


def test_capped_goal_overflow_redistributed():
    small, big = goal("Small", 100), goal("Big", 100000)
    allocs = {a.goal_name: a.amount for a in split_savings(Decimal("1000"), [small, big], "equal")}
    assert allocs["Small"] == Decimal("100.00")
    assert allocs["Big"] == Decimal("900.00")


def test_deadline_mode_favours_urgent_goal():
    today = date(2026, 10, 15)
    soon = goal("Soon", 120000, deadline=date(2026, 12, 15))
    later = goal("Later", 120000, deadline=date(2027, 10, 15))
    allocs = {a.goal_name: a.amount for a in split_savings(Decimal("10000"), [soon, later], "deadline", today)}
    assert allocs["Soon"] > allocs["Later"]
    assert sum(allocs.values()) == Decimal("10000.00")


def test_no_goals_goes_to_general_savings():
    allocs = split_savings(Decimal("500"), [], "equal")
    assert allocs[0].goal_id is None and allocs[0].amount == Decimal("500.00")


def test_regex_parse_debit_alert():
    text = ("Dear Customer, PKR 1,850.00 has been debited from your A/C ****4321 at KFC DHA on 15-Oct-2026. "
            "Available Balance PKR 48,150.00")
    parsed = regex_parse(text)
    assert parsed["direction"] == "debit"
    assert parsed["amount"] == 1850.0
    assert parsed["balance_after"] == 48150.0
    assert parsed["last4"] == "4321"
    assert parsed["merchant"].startswith("KFC")


def test_regex_parse_credit_alert():
    parsed = regex_parse("Rs. 100,000 credited to your account xx9876 via IBFT. Current balance Rs. 150,000")
    assert parsed["direction"] == "credit" and parsed["amount"] == 100000.0


def test_normalize_merchant():
    assert normalize_name("KFC PAKISTAN (PVT) LTD - DHA") == "kfc"
    assert normalize_name("Imtiaz Super Market") == "imtiaz super market"


def test_simulated_alerts_parse_like_real_ones():
    from app.models import Bank, BankAccount, Card
    from app.services.test_alerts import build_alert

    bank = Bank(name="Meezan Bank", short_name="Meezan", email_domains=["meezanbank.com"])
    account = BankAccount(balance=Decimal("50000"), last4="4821")
    card = Card(network="visa", card_type="debit")
    for direction in ("debit", "credit"):
        subject, text, _html, info = build_alert(bank, account, card, direction)
        parsed = regex_parse(f"{subject}. {text}")
        assert parsed["direction"] == direction
        assert parsed["amount"] == info["amount"]
        assert parsed["last4"] == "4821"
        expected = 50000 - info["amount"] if direction == "debit" else 50000 + info["amount"]
        assert parsed["balance_after"] == expected


class FakeSession:
    """Just enough of an AsyncSession for record_transaction with a known account."""

    def __init__(self, account):
        self.account = account

    async def scalar(self, _):
        return None

    async def get(self, model, _):
        return {"BankAccount": self.account, "Category": object()}.get(model.__name__)

    def add(self, _):
        pass

    async def flush(self):
        pass


def test_old_bank_alerts_do_not_change_a_stated_balance():
    import asyncio
    from datetime import UTC, datetime

    from app.models import BankAccount
    from app.services.finance import record_transaction

    stated = datetime(2026, 10, 19, 10, 0, tzinfo=UTC)
    acc = BankAccount(id=uuid.uuid4(), balance=Decimal(0), balance_as_of=stated)
    s = FakeSession(acc)

    async def tx(amount, direction, when, source="gmail", balance_after=None):
        await record_transaction(s, uuid.uuid4(), amount=amount, direction=direction, occurred_at=when,
                                 account_id=acc.id, category="misc", source=source, is_income=False,
                                 balance_after=balance_after)

    async def run():
        await tx(150000, "debit", datetime(2026, 9, 23, tzinfo=UTC))  # already in the stated 0
        assert acc.balance == Decimal(0)
        await tx(500, "debit", datetime(2026, 10, 19, 12, 0, tzinfo=UTC))  # after it: applies
        assert acc.balance == Decimal("-500.00")
        await tx(1000, "credit", datetime(2026, 9, 1, tzinfo=UTC), source="chat")  # told in chat: always applies
        assert acc.balance == Decimal("500.00")
        await tx(200, "debit", datetime(2026, 10, 19, 13, 0, tzinfo=UTC), balance_after=9800)  # alert states it
        assert acc.balance == Decimal("9800.00") and acc.balance_as_of == datetime(2026, 10, 19, 13, 0, tzinfo=UTC)
        await tx(300, "debit", datetime(2026, 10, 19, 12, 30, tzinfo=UTC))  # older than that alert: counted
        assert acc.balance == Decimal("9800.00")

    asyncio.run(run())


def test_merchant_names_from_real_alerts():
    from app.services.gmail import find_merchant
    from app.services.text import transaction_title

    # NayaPay: the subject says it all; the body's "sent to this email" must never become the merchant.
    assert find_merchant("You spent Rs. 375.44 at SHOPIFY* 608021774 SINGAPORE SG 💳", "sent to this email") == \
        "Shopify Singapore"
    assert find_merchant("You spent Rs. 5,924.29 at ANTHROPIC* CLAUDE SUB +14152360599 US 💳") == "Anthropic Claude SUB"
    assert find_merchant("You sent Rs. 2,500 to Chainfore (Private) Limited 💸") == "Chainfore (Private) Limited"
    assert find_merchant("You got Rs. 5,000 from Muhammad Osama Khan 🎉") == "Muhammad Osama Khan"
    assert transaction_title(find_merchant("You subscribed to a mobile bundle of Rs. 1,700 📱"),
                             "You subscribed to a mobile bundle of Rs. 1,700 📱") == "Mobile bundle"
    assert transaction_title("", "Cash withdrawal of Rs. 2,000 🏧") == "Cash withdrawal"
    # Meezan: the payee is in the details block; the footer's "contact us at 111-331-331" is not a name.
    body = ("Dear Customer, PKR 150,000.00 sent from your account xxx3319 with the following details: "
            "Beneficiary Account Title: : M.FAHEEM Branch : S.FAISAL COLONY KHI")
    assert find_merchant("Debit Transaction Alert", body) == "M.Faheem"
    assert find_merchant("", "PKR 8,000.00 received to your account xxx3319 with the following details: "
                             "Beneficiary Account : ALFALAH-xxx9816 Branch : S.FAISAL") == "Alfalah"
    assert find_merchant("Transaction Alert", "PKR 10,025.00 has been debited at 00:01 on 23-Sep-2026. Please "
                                              "do not hesitate to contact us at 111-331-331 or visit") == ""


def test_cards_must_exist_in_the_catalog():
    from app.models import CardProduct
    from app.services.cards import match_card

    meezan = [CardProduct(name=n, network=net, tier=t, card_type="debit") for n, net, t in [
        ("Meezan Mastercard Classic Debit Card", "mastercard", "classic"),
        ("Meezan Mastercard Titanium Debit Card", "mastercard", "titanium"),
        ("Meezan World Debit Card", "mastercard", "world"),
        ("Meezan Visa Classic Debit Card", "visa", "classic"),
        ("Meezan Visa Gold Debit Card", "visa", "gold"),
        ("Meezan PayPak Debit Card", "paypak", "basic"),
    ]]
    # Exists: saved as the catalog card.
    assert match_card(meezan, "visa", "debit", "Gold").product.name == "Meezan Visa Gold Debit Card"
    assert match_card(meezan, "paypak", "debit", None).product.name == "Meezan PayPak Debit Card"
    # "Mastercard Silver" doesn't exist: nothing saved, nearest real Mastercard first.
    m = match_card(meezan, "mastercard", "debit", "silver")
    assert m.product is None and m.closest[0].name == "Meezan Mastercard Classic Debit Card"
    # No tier and several Mastercards: ask which one.
    m = match_card(meezan, "mastercard", "debit", None)
    assert m.product is None and len(m.options) == 3
    # Meezan issues no credit cards in the catalog: suggest, never save.
    assert match_card(meezan, "visa", "credit", "gold").product is None
