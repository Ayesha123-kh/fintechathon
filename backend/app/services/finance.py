"""Money logic shared by the REST API, MCP tools, Gmail ingestion and scheduled jobs.

All functions take a session that is already scoped to the user (RLS), except the
merchant directory upsert, which writes a global table through a system session.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.db import system_session
from app.models import (
    Bank,
    BankAccount,
    Category,
    Deal,
    DealRedemption,
    Goal,
    Merchant,
    SavingsEntry,
    Transaction,
    UserProfile,
)
from app.services.categorize import categorize
from app.services.merchant_screen import classify_payee, status_for
from app.services.text import normalize_name, transaction_title

log = logging.getLogger(__name__)
CENT = Decimal("0.01")


def money(x) -> Decimal:
    return Decimal(str(x or 0)).quantize(CENT)


# ---------------------------------------------------------------- merchants

async def resolve_merchant(name: str, description: str = "") -> tuple[uuid.UUID | None, str]:
    """Find or create the merchant in the global directory. Returns (merchant_id, category)."""
    if not name.strip():
        cat, _ = await categorize("", description)
        return None, cat
    key = normalize_name(name)
    async with system_session() as s:
        merchant = (await s.execute(select(Merchant).where(Merchant.normalized_name == key))).scalar_one_or_none()
        if merchant:
            merchant.seen_in_transactions += 1
            return merchant.id, merchant.category_slug
    category, sub = await categorize(name, description)
    if category in ("transfer", "income"):
        return None, category
    # The self-hosted model decides whether this is a business the deal bots may look up or a private payee.
    status = status_for(await classify_payee(name, description))
    async with system_session() as s:
        # A business starts as 'pending': the deal Source Scout will find its website and socials.
        row = await s.execute(
            insert(Merchant)
            .values(name=name.strip()[:160], normalized_name=key, category_slug=category, subcategory=sub,
                    seen_in_transactions=1, sources_status=status)
            .on_conflict_do_update(index_elements=["normalized_name"],
                                   set_={"seen_in_transactions": Merchant.seen_in_transactions + 1})
            .returning(Merchant.id, Merchant.category_slug)
        )
        mid, cat = row.one()
        return mid, cat


# ---------------------------------------------------------------- transactions

async def record_transaction(
    s: AsyncSession,
    user_id: uuid.UUID,
    *,
    amount,
    direction: str,
    occurred_at: datetime | None = None,
    merchant: str = "",
    description: str = "",
    account_id: uuid.UUID | None = None,
    category: str | None = None,
    channel: str = "other",
    source: str = "manual",
    external_id: str | None = None,
    balance_after=None,
    is_income: bool | None = None,
) -> Transaction | None:
    """Insert a transaction, keep the account balance in sync and allocate income to goals.

    Returns None when `external_id` was already recorded (idempotent ingestion).
    """
    if external_id:
        exists = await s.scalar(select(Transaction.id).where(Transaction.external_id == external_id))
        if exists:
            return None
    amount = money(abs(Decimal(str(amount))))
    direction = "credit" if direction == "credit" else "debit"
    merchant_id, merchant_cat = await resolve_merchant(merchant, description) if merchant else (None, None)
    if not category:
        category = merchant_cat or (await categorize(merchant, description))[0]
    if category and not await s.get(Category, category):
        category = "misc"
    if direction == "debit" and category == "income":  # money going out is never income
        category = "misc"
    profile = await s.get(UserProfile, user_id)
    if is_income is None:
        is_income = direction == "credit" and (
            category == "income"
            or (profile and profile.monthly_income and amount >= money(profile.monthly_income) * Decimal("0.6"))
        )
    if is_income:
        category = "income"

    occurred_at = occurred_at or datetime.now(UTC)
    tx = Transaction(
        user_id=user_id, account_id=account_id, occurred_at=occurred_at, amount=amount,
        direction=direction, merchant_raw=merchant[:200], merchant_id=merchant_id, category_slug=category or "misc",
        description=description, channel=channel, source=source, external_id=external_id,
        balance_after=money(balance_after) if balance_after is not None else None, is_income=bool(is_income),
    )
    s.add(tx)
    await s.flush()

    if account_id:
        account = await s.get(BankAccount, account_id)
        # An imported alert older than the last known balance is already counted in it (e.g. the person said
        # "I have 0 in Meezan", then Gmail brought in last month's alerts). Things told in chat always apply.
        already_counted = source == "gmail" and account and account.balance_as_of and occurred_at <= account.balance_as_of
        if account and not already_counted:
            if balance_after is not None:
                account.balance = money(balance_after)
                account.balance_as_of = occurred_at
            else:
                account.balance = money(account.balance) + (amount if direction == "credit" else -amount)

    if is_income and profile:
        await allocate_income(s, user_id, amount, account_id=account_id, transaction_id=tx.id)
    if direction == "debit" and merchant_id and not is_income:
        await _detect_deal_use(s, user_id, tx)
    return tx


async def _detect_deal_use(s: AsyncSession, user_id: uuid.UUID, tx: Transaction) -> None:
    """If this purchase uses a deal the person was told about, count the saving. Never blocks the transaction."""
    from app.services.deal_detect import detect_redemption

    try:
        async with s.begin_nested():
            await detect_redemption(s, user_id, tx)
    except Exception:
        log.exception("deal detection failed for transaction %s", tx.id)


# ---------------------------------------------------------------- savings allocation

@dataclass
class Allocation:
    goal_id: uuid.UUID | None
    goal_name: str
    amount: Decimal


def _months_left(deadline: date | None, today: date) -> Decimal:
    if not deadline:
        return Decimal(12)
    months = (deadline.year - today.year) * 12 + (deadline.month - today.month)
    if deadline.day >= today.day:
        months += 1
    return Decimal(max(months, 1))


def split_savings(total: Decimal, goals: list[Goal], mode: str, today: date | None = None) -> list[Allocation]:
    """Divide `total` between active goals. Never over-fills a goal; overflow goes to general savings."""
    today = today or clock.today()
    goals = [g for g in goals if g.status == "active" and money(g.target_amount) > money(g.saved_amount)]
    if total <= 0:
        return []
    if not goals:
        return [Allocation(None, "General savings", money(total))]

    def remaining(g: Goal) -> Decimal:
        return money(g.target_amount) - money(g.saved_amount)

    if mode == "equal":
        weights = {g.id: Decimal(1) for g in goals}
    elif mode == "priority":
        weights = {g.id: Decimal(6 - max(1, min(5, g.priority))) for g in goals}
    elif mode == "custom" and any(g.weight for g in goals):
        weights = {g.id: Decimal(str(g.weight or 0)) for g in goals}
    else:  # deadline: what each goal needs per month to finish on time
        weights = {g.id: remaining(g) / _months_left(g.deadline, today) for g in goals}

    result: dict[uuid.UUID | None, Decimal] = {}
    pool = money(total)
    active = list(goals)
    # Distribute, re-distributing what capped goals could not take.
    for _ in range(len(goals) + 1):
        wsum = sum(weights[g.id] for g in active)
        if pool <= 0 or not active or wsum <= 0:
            break
        next_active, spent = [], Decimal(0)
        for g in active:
            share = (pool * weights[g.id] / wsum).quantize(CENT, rounding=ROUND_DOWN)
            room = remaining(g) - result.get(g.id, Decimal(0))
            give = min(share, room)
            result[g.id] = result.get(g.id, Decimal(0)) + give
            spent += give
            if give < room:
                next_active.append(g)
        pool -= spent
        if not next_active or len(next_active) == len(active):
            break
        active = next_active
    if 0 < pool < 1:
        # Rounding dust goes to the first goal that still has room instead of "general savings".
        for g in goals:
            if remaining(g) - result.get(g.id, Decimal(0)) >= pool:
                result[g.id] = result.get(g.id, Decimal(0)) + pool
                pool = Decimal(0)
                break
    if pool > 0:
        result[None] = result.get(None, Decimal(0)) + pool
    names = {g.id: g.name for g in goals}
    return [Allocation(gid, names.get(gid, "General savings"), money(a)) for gid, a in result.items() if a > 0]


async def monthly_savings_target(profile: UserProfile, income: Decimal) -> Decimal:
    value = money(profile.savings_value)
    if profile.savings_mode == "fixed":
        return min(value, income)
    if profile.savings_mode == "leftover":
        return Decimal(0)  # handled by the month-end job
    pct = value if value > 0 else Decimal(20)
    return money(income * pct / 100)


async def add_savings(
    s: AsyncSession, user_id: uuid.UUID, allocations: list[Allocation], source: str, note: str = "",
    account_id: uuid.UUID | None = None, transaction_id: uuid.UUID | None = None,
) -> list[Goal]:
    """Write ledger entries; returns goals that just got completed."""
    completed: list[Goal] = []
    for a in allocations:
        s.add(SavingsEntry(user_id=user_id, goal_id=a.goal_id, account_id=account_id, amount=a.amount,
                           source=source, note=note, transaction_id=transaction_id))
        if a.goal_id:
            goal = await s.get(Goal, a.goal_id)
            if goal:
                goal.saved_amount = money(goal.saved_amount) + a.amount
                if goal.status == "active" and goal.saved_amount >= money(goal.target_amount):
                    goal.status = "completed"
                    completed.append(goal)
    await s.flush()
    return completed


async def allocate_income(
    s: AsyncSession, user_id: uuid.UUID, income: Decimal, account_id=None, transaction_id=None,
) -> list[Allocation]:
    profile = await s.get(UserProfile, user_id)
    if not profile:
        return []
    target = await monthly_savings_target(profile, income)
    goals = list((await s.execute(select(Goal).where(Goal.status == "active"))).scalars())
    allocations = split_savings(target, goals, profile.goal_split_mode)
    completed = await add_savings(s, user_id, allocations, "allocation", "Monthly savings from income",
                                  account_id=account_id, transaction_id=transaction_id)
    _queue_goal_notifications(user_id, completed)
    return allocations


def _queue_goal_notifications(user_id: uuid.UUID, completed: list[Goal]) -> None:
    if not completed:
        return
    import asyncio

    from app.services.notify import notify

    for goal in completed:
        asyncio.get_running_loop().create_task(notify(
            user_id, "goal", "Goal reached! 🎉",
            f"You've fully saved for “{goal.name}”. Mubarak ho!", url=f"/goals/{goal.id}",
        ))


# ---------------------------------------------------------------- deals

async def redeem_deal(
    s: AsyncSession, user_id: uuid.UUID, amount_spent, amount_saved, deal_id: uuid.UUID | None = None,
    goal_id: uuid.UUID | None = None, transaction_id: uuid.UUID | None = None,
) -> DealRedemption:
    """The user availed a suggested discount: the amount saved goes to their savings."""
    saved = money(amount_saved)
    redemption = DealRedemption(user_id=user_id, deal_id=deal_id, amount_spent=money(amount_spent),
                                amount_saved=saved, goal_id=goal_id, transaction_id=transaction_id)
    s.add(redemption)
    if saved > 0:
        if goal_id:
            allocations = [Allocation(goal_id, "", saved)]
        else:
            profile = await s.get(UserProfile, user_id)
            goals = list((await s.execute(select(Goal).where(Goal.status == "active"))).scalars())
            allocations = split_savings(saved, goals, profile.goal_split_mode if profile else "deadline")
        title = ""
        if deal_id:
            deal = await s.get(Deal, deal_id)
            title = deal.title if deal else ""
        completed = await add_savings(s, user_id, allocations, "deal_saving", f"Saved with deal: {title}".strip())
        _queue_goal_notifications(user_id, completed)
    await s.flush()
    return redemption


# ---------------------------------------------------------------- dashboard

async def dashboard(s: AsyncSession, user_id: uuid.UUID) -> dict:
    month_start = clock.month_start()
    week_ago = datetime.now(UTC) - timedelta(days=7)

    accounts = (await s.execute(
        select(BankAccount, Bank).join(Bank, Bank.id == BankAccount.bank_id).order_by(BankAccount.created_at)
    )).all()
    savings_by_account = dict((await s.execute(
        select(SavingsEntry.account_id, func.coalesce(func.sum(SavingsEntry.amount), 0)).group_by(SavingsEntry.account_id)
    )).all())
    total_savings = money(sum(savings_by_account.values(), Decimal(0)))
    total_balance = money(sum((money(a.balance) for a, _ in accounts), Decimal(0)))
    # Savings not tied to an account are spread proportionally over balances for the bank breakdown.
    unassigned = money(savings_by_account.get(None, 0))
    banks = []
    for account, bank in accounts:
        earmarked = money(savings_by_account.get(account.id, 0))
        if unassigned and total_balance > 0:
            earmarked += money(unassigned * money(account.balance) / total_balance)
        banks.append({
            "account_id": str(account.id), "bank": bank.name, "bank_short": bank.short_name,
            "nickname": account.nickname, "account_type": account.account_type,
            "balance": money(account.balance), "savings": min(earmarked, max(money(account.balance), Decimal(0))),
            "expendable": max(money(account.balance) - earmarked, Decimal(0)),
        })

    goals = (await s.execute(select(Goal).where(Goal.status.in_(["active", "completed", "paused"]))
                             .order_by(Goal.status, Goal.deadline.nulls_last()))).scalars().all()
    today = clock.today()
    goal_rows = []
    for g in goals:
        remaining = max(money(g.target_amount) - money(g.saved_amount), Decimal(0))
        months = _months_left(g.deadline, today)
        goal_rows.append({
            "id": str(g.id), "name": g.name, "icon": g.icon, "status": g.status,
            "target": money(g.target_amount), "saved": money(g.saved_amount), "deadline": g.deadline,
            "progress": float(min(Decimal(1), money(g.saved_amount) / money(g.target_amount))) if g.target_amount else 0,
            "monthly_needed": money(remaining / months) if remaining else Decimal(0),
        })

    spend_rows = (await s.execute(
        select(Transaction.category_slug, Category.name, Category.color, func.sum(Transaction.amount))
        .join(Category, Category.slug == Transaction.category_slug)
        .where(Transaction.direction == "debit", Transaction.occurred_at >= month_start,
               Transaction.category_slug.notin_(["transfer"]))
        .group_by(Transaction.category_slug, Category.name, Category.color)
        .order_by(func.sum(Transaction.amount).desc())
    )).all()
    income_month = money(await s.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(Transaction.is_income.is_(True), Transaction.occurred_at >= month_start)))
    saved_week = money(await s.scalar(
        select(func.coalesce(func.sum(SavingsEntry.amount), 0))
        .where(SavingsEntry.created_at >= week_ago, SavingsEntry.amount > 0)))
    saved_month = money(await s.scalar(
        select(func.coalesce(func.sum(SavingsEntry.amount), 0))
        .where(SavingsEntry.created_at >= month_start, SavingsEntry.amount > 0)))
    deal_savings = money(await s.scalar(select(func.coalesce(func.sum(DealRedemption.amount_saved), 0))))
    deal_savings_month = money(await s.scalar(
        select(func.coalesce(func.sum(DealRedemption.amount_saved), 0))
        .where(DealRedemption.created_at >= month_start)))
    # This month's salary is in once an income credit reaches 60% of the stated monthly income (the bar
    # record_transaction uses to recognise a salary); before an income is stated, any income credit counts.
    profile = await s.get(UserProfile, user_id)
    salary_floor = money(profile.monthly_income) * Decimal("0.6") if profile and profile.monthly_income else Decimal(0)
    salary_credited = await s.scalar(select(Transaction.id).where(
        Transaction.is_income.is_(True), Transaction.occurred_at >= month_start, Transaction.amount >= salary_floor,
    ).limit(1)) is not None
    recent = (await s.execute(select(Transaction).order_by(Transaction.occurred_at.desc()).limit(25))).scalars().all()

    return {
        "currency": "PKR",
        "total_balance": total_balance,
        "total_savings": total_savings,
        "expendable": max(total_balance - total_savings, Decimal(0)),
        "saved_this_week": saved_week,
        "saved_this_month": saved_month,
        "deal_savings_total": deal_savings,
        "deal_savings_this_month": deal_savings_month,
        "income_this_month": income_month,
        "salary_credited_this_month": salary_credited,
        "spent_this_month": money(sum((r[3] for r in spend_rows), Decimal(0))),
        "banks": banks,
        "goals": goal_rows,
        "spending_by_category": [
            {"category": slug, "name": name, "color": color, "amount": money(total)}
            for slug, name, color, total in spend_rows
        ],
        "recent_transactions": [
            {"id": str(t.id), "occurred_at": t.occurred_at, "amount": money(t.amount), "direction": t.direction,
             "merchant": transaction_title(t.merchant_raw, t.description), "category": t.category_slug, "source": t.source}
            for t in recent
        ],
    }
