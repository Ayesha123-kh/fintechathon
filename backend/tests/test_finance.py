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
