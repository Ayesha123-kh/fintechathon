"""`fin_user` MCP server: the tools a user's private bots use to read and change that user's data.

OpenMausBot sends no caller identity to MCP servers, so every tool takes the `member_key`
from the user's room bulletin. The key resolves to one user and the database session is
scoped to that user with RLS, so a tool can never touch another person's rows.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.cache import rate_limit
from app.core.db import scoped_session
from app.mcp.common import out
from app.models import (
    Bank,
    BankAccount,
    Card,
    CardProduct,
    Category,
    CoverageRequest,
    Deal,
    DealRedemption,
    EmailConnection,
    Goal,
    MarketSignal,
    ResearchNote,
    SavingsEntry,
    Transaction,
    User,
    UserFact,
    UserFollow,
    UserProfile,
    WatchCluster,
)
from app.services import deal_detect, finance
from app.services.cards import match_card
from app.services.deals import estimate_saving
from app.services.deals import find_deals as find_deals_svc
from app.services.notify import notify
from app.services.omb import refresh_room, user_id_for_member_key
from app.services.text import transaction_title

mcp = FastMCP(
    "fin_user",
    instructions=(
        "Personal finance tools for ONE user. Always pass the member_key from your room bulletin. "
        "Amounts are in PKR. Read before advising; write whenever the person tells you a new fact."
    ),
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


class ToolError(Exception):
    pass


@asynccontextmanager
async def member(member_key: str) -> AsyncIterator[tuple[AsyncSession, uuid.UUID]]:
    user_id = await user_id_for_member_key(member_key or "")
    if not user_id:
        if not await rate_limit("mk:invalid", 50, 60):
            await asyncio.sleep(2)
        raise ToolError("Unknown member_key. Copy it exactly from the room bulletin.")
    # Per person: keys are random words, so a prefix of the key could be shared by several people.
    if not await rate_limit(f"mk:{user_id}", 600, 60):
        raise ToolError("Too many calls, slow down.")
    async with scoped_session(user_id, "user") as s:
        yield s, user_id


async def _bank_by_name(s: AsyncSession, name: str) -> Bank:
    q = name.strip().lower()
    banks = list((await s.execute(select(Bank))).scalars())
    for b in banks:
        if q in (b.name.lower(), b.short_name.lower()) or q in [a.lower() for a in b.aliases]:
            return b
    for b in banks:
        if q in b.name.lower() or b.short_name.lower() in q:
            return b
    raise ToolError(f"Unknown bank '{name}'. Call list_banks to see supported banks and wallets.")


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError as exc:
        raise ToolError(f"Dates must be YYYY-MM-DD, got '{value}'.") from exc


# ------------------------------------------------------------------ overview & profile

@mcp.tool()
async def get_overview(member_key: str) -> dict:
    """Everything about the person at a glance: profile, onboarding progress, banks, cards, goals,
    balances (total / savings / expendable), this month's spending by category and remembered facts."""
    async with member(member_key) as (s, uid):
        user = await s.get(User, uid)
        profile = await s.get(UserProfile, uid)
        cards = (await s.execute(select(Card, Bank.name).join(Bank, Bank.id == Card.bank_id))).all()
        facts = (await s.execute(select(UserFact).where(UserFact.superseded_at.is_(None))
                                 .order_by(UserFact.created_at.desc()).limit(30))).scalars().all()
        email = await s.scalar(select(func.count()).select_from(EmailConnection)
                               .where(EmailConnection.status == "active"))
        dash = await finance.dashboard(s, uid)
        missing = []
        if not dash["banks"]:
            missing.append("bank accounts")
        if not cards:
            missing.append("debit/credit cards")
        if not profile or not profile.monthly_income:
            missing.append("monthly income and salary day")
        if not dash["goals"]:
            missing.append("saving goals")
        if not profile or profile.savings_value is None and profile.savings_mode != "leftover":
            missing.append("how much to save each month")
        if not email:
            missing.append("email inbox connection (optional, for automatic transaction tracking)")
        if profile and not (profile.onboarding_state or {}).get("sadqah_asked"):
            missing.append("whether they want sadqah reminders")
        if profile and not (profile.onboarding_state or {}).get("investment_asked"):
            missing.append("whether they want the optional investment advisory board")
        return out({
            "name": user.full_name, "onboarding_completed": user.onboarding_completed,
            "onboarding_missing": missing,
            "profile": {
                "monthly_income": profile.monthly_income, "salary_day": profile.salary_day, "city": profile.city,
                "language": profile.language, "savings_mode": profile.savings_mode,
                "savings_value": profile.savings_value, "goal_split_mode": profile.goal_split_mode,
                "sadqah": {"opt_in": profile.sadqah_opt_in, "mode": profile.sadqah_mode,
                           "value": profile.sadqah_value, "frequency": profile.sadqah_frequency},
                "investment_opt_in": profile.investment_opt_in, "risk_profile": profile.risk_profile,
                "preferred_places": profile.preferred_places,
            } if profile else None,
            "cards": [{"id": str(c.id), "label": c.label, "bank": bank, "network": c.network, "tier": c.tier,
                       "type": c.card_type} for c, bank in cards],
            "email_connected": bool(email),
            "remembered_facts": [{"id": str(f.id), "fact": f.fact, "category": f.category,
                                  "date": f.created_at.date()} for f in facts],
            **{k: dash[k] for k in ("total_balance", "total_savings", "expendable", "saved_this_week",
                                    "income_this_month", "spent_this_month", "banks", "goals",
                                    "spending_by_category", "deal_savings_total")},
        })


@mcp.tool()
async def update_profile(
    member_key: str,
    monthly_income: float | None = None,
    salary_day: int | None = None,
    city: str | None = None,
    language: Literal["en", "ur", "roman_ur"] | None = None,
    savings_mode: Literal["percent", "fixed", "leftover"] | None = None,
    savings_value: float | None = None,
    goal_split_mode: Literal["equal", "priority", "custom", "deadline"] | None = None,
    risk_profile: Literal["conservative", "moderate", "aggressive"] | None = None,
    preferred_places: list[str] | None = None,
) -> dict:
    """Update the financial profile. savings_mode: 'percent' of income (savings_value = %), 'fixed' amount
    per month (savings_value = PKR) or 'leftover' (whatever is unspent at month end). goal_split_mode decides
    how monthly savings are divided between simultaneous goals: equal, priority (1 = highest), custom
    (each goal's weight %) or deadline (what each goal needs per month to finish on time).
    When income changes (e.g. an increment) ALSO call remember_fact so advice adapts.
    language: set 'roman_ur' during onboarding once they answer in Urdu (any script); after that change it
    only when the person explicitly asks for another language ('ur' = Urdu script, only on request)."""
    async with member(member_key) as (s, uid):
        p = await s.get(UserProfile, uid)
        changes = {k: v for k, v in {
            "monthly_income": monthly_income, "salary_day": salary_day, "city": city, "language": language,
            "savings_mode": savings_mode, "savings_value": savings_value, "goal_split_mode": goal_split_mode,
            "risk_profile": risk_profile, "preferred_places": preferred_places,
        }.items() if v is not None}
        if salary_day is not None and not 1 <= salary_day <= 31:
            raise ToolError("salary_day must be 1-31")
        if savings_mode == "percent" and savings_value is not None and not 0 <= savings_value <= 90:
            raise ToolError("Savings percent must be between 0 and 90.")
        for k, v in changes.items():
            setattr(p, k, v)
    if "language" in changes:
        asyncio.get_running_loop().create_task(refresh_room(uid))
    return {"ok": True, "updated": list(changes)}


@mcp.tool()
async def set_sadqah_preferences(
    member_key: str,
    opt_in: bool,
    mode: Literal["percent_income", "fixed"] | None = None,
    value: float | None = None,
    frequency: Literal["weekly", "friday", "monthly"] | None = None,
) -> dict:
    """Record whether the person wants sadqah (charity) reminders and how. Only ask once; respect a 'no'."""
    async with member(member_key) as (s, uid):
        p = await s.get(UserProfile, uid)
        p.sadqah_opt_in = opt_in
        if opt_in:
            p.sadqah_mode, p.sadqah_value, p.sadqah_frequency = mode or "fixed", value, frequency or "friday"
        p.onboarding_state = {**(p.onboarding_state or {}), "sadqah_asked": True}
    return {"ok": True}


@mcp.tool()
async def set_investment_opt_in(member_key: str, opt_in: bool, disclaimer_accepted: bool = False) -> dict:
    """Turn the optional investment advisory board on/off. Before opting in you MUST show this disclaimer
    and get explicit agreement, then pass disclaimer_accepted=true:
    'Investment insights are educational and generated by AI from public data. They are not licensed
    financial advice, can be wrong, and past performance does not guarantee future results. Investing
    involves risk of loss, including crypto which is not regulated by SBP. Decide independently or consult a
    SECP-licensed advisor.'"""
    async with member(member_key) as (s, uid):
        p = await s.get(UserProfile, uid)
        p.onboarding_state = {**(p.onboarding_state or {}), "investment_asked": True}
        if opt_in and not disclaimer_accepted:
            return {"ok": False, "error": "Show the disclaimer and get explicit agreement first."}
        p.investment_opt_in = opt_in
        if opt_in:
            p.investment_disclaimer_accepted_at = datetime.now(UTC)
    asyncio.get_running_loop().create_task(refresh_room(uid))
    return {"ok": True, "investment_opt_in": opt_in,
            "note": "The Investment Advisor joins this chat shortly." if opt_in else "Investment Advisor removed."}


@mcp.tool()
async def complete_onboarding(member_key: str) -> dict:
    """Mark onboarding finished once banks, cards, income, savings rule and at least one goal are known."""
    async with member(member_key) as (s, uid):
        user = await s.get(User, uid)
        user.onboarding_completed = True
    asyncio.get_running_loop().create_task(refresh_room(uid))
    return {"ok": True}


# ------------------------------------------------------------------ memory

@mcp.tool()
async def remember_fact(member_key: str, fact: str, category: str = "general",
                        replaces_fact_id: str | None = None) -> dict:
    """Save a lasting fact about the person (life events, increments, preferences, family, habits).
    If it updates an older fact, pass that fact's id as replaces_fact_id."""
    async with member(member_key) as (s, uid):
        if replaces_fact_id:
            old = await s.get(UserFact, uuid.UUID(replaces_fact_id))
            if old:
                old.superseded_at = datetime.now(UTC)
        f = UserFact(user_id=uid, fact=fact.strip()[:1000], category=category[:40])
        s.add(f)
        await s.flush()
        return {"ok": True, "id": str(f.id)}


@mcp.tool()
async def forget_fact(member_key: str, fact_id: str) -> dict:
    """Retire a remembered fact that is no longer true."""
    async with member(member_key) as (s, _):
        f = await s.get(UserFact, uuid.UUID(fact_id))
        if f:
            f.superseded_at = datetime.now(UTC)
    return {"ok": True}


# ------------------------------------------------------------------ banks & cards

@mcp.tool()
async def list_banks(member_key: str) -> list[dict]:
    """Supported Pakistani banks and wallets (names to use with add_bank_account / add_card)."""
    async with member(member_key) as (s, _):
        banks = (await s.execute(select(Bank).order_by(Bank.name))).scalars()
        return [{"name": b.name, "short": b.short_name, "kind": b.kind} for b in banks]


def _product_row(p: CardProduct) -> dict:
    return {"name": p.name, "network": p.network, "tier": p.tier, "type": p.card_type, "islamic": p.is_islamic,
            "confidence": p.confidence}


@mcp.tool()
async def list_card_products(member_key: str, bank: str, card_type: Literal["debit", "credit"] | None = None) -> list[dict]:
    """The cards a bank issues (name, network, tier, debit/credit), from our catalog. Offer these when the person
    adds a card so names and tiers stay consistent. 'confidence' is how sure we are the card still exists
    (official > bank_site > weak); a null network means the bank's page did not say, so ask the person.
    Only these cards can be saved with add_card; if the person names one that isn't listed, ask which of these
    they mean."""
    async with member(member_key) as (s, _):
        b = await _bank_by_name(s, bank)
        stmt = select(CardProduct).where(CardProduct.bank_id == b.id).order_by(CardProduct.card_type, CardProduct.name)
        if card_type:
            stmt = stmt.where(CardProduct.card_type == card_type)
        return [_product_row(p) for p in (await s.execute(stmt)).scalars()]


@mcp.tool()
async def add_bank_account(member_key: str, bank: str, account_type: Literal["current", "savings", "wallet"] = "current",
                           balance: float | None = None, nickname: str = "", last4: str | None = None) -> dict:
    """Add a bank account or wallet the person actively uses."""
    async with member(member_key) as (s, uid):
        b = await _bank_by_name(s, bank)
        count = await s.scalar(select(func.count()).select_from(BankAccount))
        acc = BankAccount(user_id=uid, bank_id=b.id, account_type=account_type, balance=balance or 0,
                          balance_as_of=datetime.now(UTC) if balance is not None else None,
                          nickname=nickname or b.short_name, last4=last4, is_primary=count == 0)
        s.add(acc)
        await s.flush()
        return {"ok": True, "account_id": str(acc.id), "bank": b.name}


@mcp.tool()
async def update_bank_account(member_key: str, account_id: str, balance: float | None = None,
                              nickname: str | None = None, last4: str | None = None,
                              is_primary: bool | None = None) -> dict:
    """Correct an account's balance or details (e.g. when the person tells you their current balance)."""
    async with member(member_key) as (s, _):
        acc = await s.get(BankAccount, uuid.UUID(account_id))
        if not acc:
            raise ToolError("No such account.")
        if balance is not None:
            acc.balance, acc.balance_as_of = balance, datetime.now(UTC)
        if nickname is not None:
            acc.nickname = nickname
        if last4 is not None:
            acc.last4 = last4
        if is_primary:
            for other in (await s.execute(select(BankAccount))).scalars():
                other.is_primary = other.id == acc.id
    return {"ok": True}


@mcp.tool()
async def remove_bank_account(member_key: str, account_id: str) -> dict:
    """Remove an account the person closed or no longer uses."""
    async with member(member_key) as (s, _):
        acc = await s.get(BankAccount, uuid.UUID(account_id))
        if acc:
            await s.delete(acc)
    return {"ok": True}


@mcp.tool()
async def add_card(member_key: str, bank: str, network: Literal["visa", "mastercard", "unionpay", "paypak", "amex"],
                   card_type: Literal["debit", "credit"] = "debit", tier: str | None = None) -> dict:
    """Save a debit/credit card, e.g. 'Visa Gold debit card of Meezan Bank' -> bank='Meezan Bank',
    network='visa', tier='gold', card_type='debit'. Cards decide which bank discounts apply.
    Only cards in our catalog of what each bank really issues can be saved. If it isn't one, nothing is saved and
    you get `did_you_mean` (closest real cards) or `which_one` (several fit): ask the person, then call again with
    the confirmed network / tier. Never save a card the person hasn't confirmed.
    Only the card TYPE is stored: never ask for or save any card digits (not even the last 4), CVV, PIN or OTP."""
    async with member(member_key) as (s, uid):
        b = await _bank_by_name(s, bank)
        products = list((await s.execute(select(CardProduct).where(CardProduct.bank_id == b.id))).scalars())
        m = match_card(products, network, card_type, tier)
        asked = f"{network.title()}{f' {tier.title()}' if tier else ''} {card_type} card"
        if m.options:
            return {"ok": False, "saved": False, "which_one": [_product_row(p) for p in m.options],
                    "ask": f"{b.name} has several {network.title()} {card_type} cards. Ask the person which one they "
                           "have, then call add_card again with its tier."}
        if not m.product:
            return {"ok": False, "saved": False, "did_you_mean": [_product_row(p) for p in m.closest],
                    "ask": f"{b.name} doesn't issue a {asked} as far as our catalog knows, so it was NOT saved. Ask "
                           f"the person, e.g. \"Did you mean the {m.closest[0].name}?\"" if m.closest else
                           f"We don't know any cards {b.name} issues, so it was NOT saved. Tell the person we can't "
                           "add this card yet."}
        p = m.product
        acc_id = await s.scalar(select(BankAccount.id).where(BankAccount.bank_id == b.id).limit(1))
        card = Card(user_id=uid, bank_id=b.id, network=p.network or network, tier=p.tier, card_type=p.card_type,
                    label=p.name, account_id=acc_id)
        s.add(card)
        await s.flush()
        return {"ok": True, "saved": True, "card_id": str(card.id), "label": card.label}


@mcp.tool()
async def remove_card(member_key: str, card_id: str) -> dict:
    """Remove a card the person no longer has."""
    async with member(member_key) as (s, _):
        card = await s.get(Card, uuid.UUID(card_id))
        if card:
            await s.delete(card)
    return {"ok": True}


# ------------------------------------------------------------------ goals & savings

@mcp.tool()
async def create_goal(member_key: str, name: str, target_amount: float, deadline: str | None = None,
                      priority: int = 3, weight: float | None = None, icon: str = "target") -> dict:
    """Create a saving goal, e.g. 'Car' Rs. 1,500,000 by 2027-04-30. deadline is YYYY-MM-DD.
    priority 1 (highest) to 5. weight is the % share used when goal_split_mode is 'custom'.
    icon: one of target, car, home, plane, graduation-cap, heart, gift, phone, laptop, ring, baby, umbrella."""
    async with member(member_key) as (s, uid):
        if target_amount <= 0:
            raise ToolError("target_amount must be positive")
        g = Goal(user_id=uid, name=name[:120], target_amount=target_amount, deadline=_parse_date(deadline),
                 priority=max(1, min(5, priority)), weight=weight, icon=icon)
        s.add(g)
        await s.flush()
        monthly = None
        if g.deadline:
            monthly = float(finance.money(target_amount) / finance._months_left(g.deadline, clock.today()))
        return {"ok": True, "goal_id": str(g.id), "monthly_needed": monthly}


@mcp.tool()
async def update_goal(member_key: str, goal_id: str, name: str | None = None, target_amount: float | None = None,
                      deadline: str | None = None, priority: int | None = None, weight: float | None = None,
                      status: Literal["active", "paused", "completed", "cancelled"] | None = None) -> dict:
    """Change a goal (target, deadline, priority, weight) or pause / cancel it."""
    async with member(member_key) as (s, _):
        g = await s.get(Goal, uuid.UUID(goal_id))
        if not g:
            raise ToolError("No such goal.")
        if name is not None:
            g.name = name
        if target_amount is not None:
            g.target_amount = target_amount
        if deadline is not None:
            g.deadline = _parse_date(deadline)
        if priority is not None:
            g.priority = max(1, min(5, priority))
        if weight is not None:
            g.weight = weight
        if status is not None:
            g.status = status
    return {"ok": True}


@mcp.tool()
async def move_to_savings(member_key: str, amount: float, goal_id: str | None = None,
                          account_id: str | None = None, note: str = "") -> dict:
    """Earmark money as savings now (whole amount to one goal, or split across goals by the person's rule
    when goal_id is omitted). Use a negative amount with goal_id to withdraw from a goal."""
    async with member(member_key) as (s, uid):
        acc = uuid.UUID(account_id) if account_id else None
        if goal_id:
            allocs = [finance.Allocation(uuid.UUID(goal_id), "", finance.money(amount))]
        else:
            if amount <= 0:
                raise ToolError("Use goal_id to withdraw.")
            p = await s.get(UserProfile, uid)
            goals = list((await s.execute(select(Goal).where(Goal.status == "active"))).scalars())
            allocs = finance.split_savings(finance.money(amount), goals, p.goal_split_mode)
        source = "manual" if amount > 0 else "withdrawal"
        completed = await finance.add_savings(s, uid, allocs, source, note, account_id=acc)
        return out({"ok": True, "allocations": [{"goal": a.goal_name, "amount": a.amount} for a in allocs],
                    "goals_completed": [g.name for g in completed]})


@mcp.tool()
async def preview_savings_split(member_key: str, amount: float) -> dict:
    """Show how an amount would be divided between active goals under the person's current rule."""
    async with member(member_key) as (s, uid):
        p = await s.get(UserProfile, uid)
        goals = list((await s.execute(select(Goal).where(Goal.status == "active"))).scalars())
        allocs = finance.split_savings(finance.money(amount), goals, p.goal_split_mode)
        return out({"mode": p.goal_split_mode, "split": [{"goal": a.goal_name, "amount": a.amount} for a in allocs]})


# ------------------------------------------------------------------ transactions

@mcp.tool()
async def record_transaction(member_key: str, amount: float, direction: Literal["debit", "credit"],
                             merchant: str = "", category: str | None = None, account_id: str | None = None,
                             occurred_at: str | None = None, note: str = "", is_income: bool | None = None) -> dict:
    """Log a transaction the person tells you about (cash spends, transfers, salary). Debits reduce and credits
    increase the account balance. Salary credits automatically move savings into goals.
    Call it ONCE per spend and never repeat a call: an identical entry within 90 seconds is refused as a duplicate.
    `category` is optional; when you give one it must be one of: food, grocery, fuel (petrol, diesel, CNG),
    medicine, transport, utilities, shopping, entertainment, education, travel, housing, telecom, charity,
    transfer, income, misc. Put what was bought in `merchant` or `note` ("petrol", "KFC") and the app picks
    the category itself. Tell the person the category name returned in `category_name`."""
    async with member(member_key) as (s, uid):
        if (dup := await finance.recent_chat_duplicate(s, amount=amount, direction=direction, merchant=merchant,
                                                         category=category)):
            cat = await s.get(Category, dup.category_slug)
            return {"ok": True, "duplicate": True, "transaction_id": str(dup.id), "category": dup.category_slug,
                    "category_name": cat.name if cat else dup.category_slug,
                    "note": "The same entry was recorded a moment ago, so it was not added again."}
        when = datetime.fromisoformat(occurred_at) if occurred_at else None
        if when and when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        tx = await finance.record_transaction(
            s, uid, amount=amount, direction=direction, merchant=merchant, category=category,
            account_id=uuid.UUID(account_id) if account_id else None, occurred_at=when, description=note,
            source="chat", is_income=is_income,
        )
        cat = await s.get(Category, tx.category_slug)
        return {"ok": True, "transaction_id": str(tx.id), "category": tx.category_slug,
                "category_name": cat.name if cat else tx.category_slug, "is_income": tx.is_income}


@mcp.tool()
async def list_transactions(member_key: str, days: int = 30, category: str | None = None,
                            merchant: str | None = None, limit: int = 40) -> list[dict]:
    """Recent transactions, newest first."""
    async with member(member_key) as (s, _):
        stmt = select(Transaction).where(Transaction.occurred_at >= datetime.now(UTC) - timedelta(days=days))
        if category:
            stmt = stmt.where(Transaction.category_slug == category)
        if merchant:
            stmt = stmt.where(Transaction.merchant_raw.ilike(f"%{merchant}%"))
        rows = (await s.execute(stmt.order_by(Transaction.occurred_at.desc()).limit(min(limit, 200)))).scalars()
        return out([{"id": t.id, "date": t.occurred_at, "amount": t.amount, "direction": t.direction,
                     "merchant": transaction_title(t.merchant_raw, t.description), "category": t.category_slug, "source": t.source} for t in rows])


@mcp.tool()
async def spending_summary(member_key: str, days: int = 30) -> dict:
    """Spending habits: totals by category, top merchants, daily average, income in the period and the
    savings rate. Use it to coach the person and to personalise discount suggestions."""
    async with member(member_key) as (s, _):
        since = datetime.now(UTC) - timedelta(days=days)
        base = select(Transaction).where(Transaction.occurred_at >= since)
        by_cat = (await s.execute(
            select(Transaction.category_slug, func.sum(Transaction.amount), func.count())
            .where(Transaction.occurred_at >= since, Transaction.direction == "debit",
                   Transaction.category_slug != "transfer")
            .group_by(Transaction.category_slug).order_by(func.sum(Transaction.amount).desc()))).all()
        top_merchants = (await s.execute(
            select(Transaction.merchant_raw, func.sum(Transaction.amount), func.count())
            .where(Transaction.occurred_at >= since, Transaction.direction == "debit", Transaction.merchant_raw != "")
            .group_by(Transaction.merchant_raw).order_by(func.count().desc()).limit(10))).all()
        income = await s.scalar(select(func.coalesce(func.sum(Transaction.amount), 0))
                                .where(Transaction.occurred_at >= since, Transaction.is_income.is_(True)))
        saved = await s.scalar(select(func.coalesce(func.sum(SavingsEntry.amount), 0))
                               .where(SavingsEntry.created_at >= since))
        spent = sum((r[1] for r in by_cat), 0)
        count = await s.scalar(select(func.count()).select_from(base.subquery()))
        return out({
            "days": days, "transactions": count, "spent": spent, "income": income, "saved": saved,
            "daily_average_spend": round(float(spent) / max(days, 1), 2),
            "savings_rate_pct": round(float(saved) / float(income) * 100, 1) if income else None,
            "by_category": [{"category": c, "amount": a, "count": n} for c, a, n in by_cat],
            "top_merchants": [{"merchant": m, "amount": a, "visits": n} for m, a, n in top_merchants],
        })


# ------------------------------------------------------------------ deals

@mcp.tool()
async def find_deals(member_key: str, category: str | None = None, merchant: str | None = None,
                     query: str | None = None, only_eligible: bool = True) -> list[dict]:
    """Current deals and discounts in Pakistan the person can use: generic deals plus bank/card deals that match
    THEIR cards, in their city, valid today, ranked by the merchants they visit most. category is one of
    food, grocery, fuel, medicine, shopping, entertainment, travel, transport, utilities, telecom, education."""
    async with member(member_key) as (s, uid):
        return await find_deals_svc(s, uid, category=category, merchant=merchant, query=query,
                                    only_eligible=only_eligible)


@mcp.tool()
async def offer_deal(member_key: str, deal_id: str) -> dict:
    """Call this for EVERY deal you recommend to the person (deal_id from find_deals). It starts tracking: when a
    debit at that merchant shows up in their bank alerts inside the deal's dates, on a card the deal accepts, the
    saving is detected automatically, moved into their savings and they are congratulated. You don't need to ask
    whether they used it or call avail_deal for those."""
    async with member(member_key) as (s, uid):
        deal = await s.get(Deal, uuid.UUID(deal_id))
        if not deal or deal.status != "active":
            raise ToolError("That deal is not active.")
        offer = await deal_detect.record_offer(s, uid, deal.id)
        return {"ok": True, "tracking": True, "merchant": deal.merchant_name, "offered_at": offer.offered_at,
                "note": "Detected automatically from their bank alerts; offers count for up to "
                        f"{deal_detect.OFFER_TTL_DAYS} days or until the deal ends."}


@mcp.tool()
async def avail_deal(member_key: str, amount_spent: float, deal_id: str | None = None,
                     amount_saved: float | None = None, goal_id: str | None = None) -> dict:
    """The person used a suggested discount. The amount saved is moved into their savings (to goal_id, or split
    across goals). If amount_saved is omitted it is estimated from the deal terms. Not needed for deals you
    offered with offer_deal and that were already detected automatically (this then reports it instead)."""
    async with member(member_key) as (s, uid):
        deal = await s.get(Deal, uuid.UUID(deal_id)) if deal_id else None
        if deal:  # already counted from their bank alert in the last two days? don't save it twice
            seen = await s.scalar(select(DealRedemption).where(
                DealRedemption.deal_id == deal.id, DealRedemption.transaction_id.is_not(None),
                DealRedemption.created_at >= datetime.now(UTC) - timedelta(days=2)).limit(1))
            if seen:
                return {"ok": True, "already_counted": True, "amount_saved": float(seen.amount_saved),
                        "note": "This purchase was already detected from their bank alert and saved."}
        if amount_saved is None:
            if not deal:
                raise ToolError("Give amount_saved or a deal_id to estimate it.")
            amount_saved = await estimate_saving(deal, amount_spent)
        await finance.redeem_deal(s, uid, amount_spent, amount_saved, deal_id=deal.id if deal else None,
                                  goal_id=uuid.UUID(goal_id) if goal_id else None)
        week = await s.scalar(select(func.coalesce(func.sum(SavingsEntry.amount), 0)).where(
            SavingsEntry.created_at >= datetime.now(UTC) - timedelta(days=7), SavingsEntry.amount > 0))
    if amount_saved and amount_saved > 0:
        asyncio.get_running_loop().create_task(notify(
            uid, "motivation", "Nice save! 💚",
            f"Rs. {amount_saved:,.0f} went to your savings. You've saved Rs. {float(week):,.0f} this week.",
        ))
    return {"ok": True, "amount_saved": amount_saved, "saved_this_week": float(week)}


# ------------------------------------------------------------------ email & notifications

@mcp.tool()
async def email_connection_status(member_key: str) -> dict:
    """Whether a Gmail inbox is connected for automatic transaction tracking. If not, tell the person to open
    Settings (the sliders icon at the top right) and tap Connect Gmail: it is read-only and only bank alerts are used."""
    async with member(member_key) as (s, _):
        rows = (await s.execute(select(EmailConnection))).scalars().all()
        return out({"connected": [{"email": r.email_address, "status": r.status, "last_synced_at": r.last_synced_at}
                                  for r in rows], "connect_where": "Settings > Email connection"})


@mcp.tool()
async def send_push_notification(member_key: str, title: str, body: str, url: str = "/dashboard") -> dict:
    """Send a push notification to the person's phone (use sparingly: reminders, a great saving, an
    important deal expiring). Max 6 per day."""
    async with member(member_key) as (_, uid):
        pass
    if not await rate_limit(f"push:{uid}:{clock.today()}", 6, 86400):
        return {"ok": False, "error": "daily notification limit reached"}
    await notify(uid, "chat", title[:120], body[:400], url=url)
    return {"ok": True}


# ------------------------------------------------------------------ investments (opt-in only)

async def _require_investor(s: AsyncSession, uid: uuid.UUID) -> None:
    p = await s.get(UserProfile, uid)
    if not p or not p.investment_opt_in:
        raise ToolError("The person has not opted in to the investment advisory board (with disclaimer).")


@mcp.tool()
async def market_signals(member_key: str, asset_class: str | None = None, symbols: list[str] | None = None,
                         hours: int = 72) -> list[dict]:
    """Latest signals from the watcher bots. asset_class: gold_silver, psx, foreign_stocks, crypto,
    pk_real_estate. Only for people who opted in to the investment board."""
    async with member(member_key) as (s, uid):
        await _require_investor(s, uid)
        stmt = select(MarketSignal).where(MarketSignal.created_at >= datetime.now(UTC) - timedelta(hours=hours))
        if asset_class:
            stmt = stmt.where(MarketSignal.asset_class == asset_class)
        if symbols:
            stmt = stmt.where(MarketSignal.symbol.in_([x.upper() for x in symbols]))
        rows = (await s.execute(stmt.order_by(MarketSignal.created_at.desc()).limit(50))).scalars()
        return out([{"symbol": r.symbol, "asset_class": r.asset_class, "signal": r.signal,
                     "confidence": r.confidence, "price": r.price, "horizon": r.horizon,
                     "rationale": r.rationale, "at": r.created_at, "by": r.created_by} for r in rows])


@mcp.tool()
async def market_research(member_key: str, asset_class: str, days: int = 7) -> list[dict]:
    """Recent research and expert analysis notes for an asset class (opt-in only)."""
    async with member(member_key) as (s, uid):
        await _require_investor(s, uid)
        rows = (await s.execute(select(ResearchNote).where(
            ResearchNote.asset_class == asset_class,
            ResearchNote.created_at >= datetime.now(UTC) - timedelta(days=days),
        ).order_by(ResearchNote.created_at.desc()).limit(15))).scalars()
        return out([{"kind": r.kind, "title": r.title, "summary": r.summary, "sentiment": r.sentiment,
                     "symbols": r.symbols, "sources": r.sources, "at": r.created_at} for r in rows])


@mcp.tool()
async def follow_asset(member_key: str, asset_class: str, symbol: str) -> dict:
    """Follow an asset. If no watcher covers it yet, a coverage request is filed so the team adds it."""
    async with member(member_key) as (s, uid):
        await _require_investor(s, uid)
        symbol = symbol.upper().strip()
        s.add(UserFollow(user_id=uid, asset_class=asset_class, symbol=symbol))
        covered = await s.scalar(select(WatchCluster.slug).where(
            WatchCluster.asset_class == asset_class, WatchCluster.symbols.contains([symbol])))
        if not covered:
            s.add(CoverageRequest(user_id=uid, asset_class=asset_class, symbol=symbol))
        return {"ok": True, "covered_by": covered,
                "note": None if covered else "Not watched yet: requested coverage from the team."}


def build_app():
    return mcp.streamable_http_app()
