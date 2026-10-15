"""Scheduled work: waking shared agent teams, Gmail sync and proactive nudges to users."""

import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select

from app.core.db import scoped_session, system_session
from app.models import AgentRegistry, ChatRoom, Merchant, SavingsEntry, Transaction, User, UserProfile
from app.services import finance
from app.services.notify import notify
from app.services.omb import GatewayError, send_to_room, trigger_bot

log = logging.getLogger(__name__)


async def _bots(kind: str, team: str | None = None) -> list[str]:
    async with system_session() as s:
        stmt = select(AgentRegistry.name).where(AgentRegistry.kind == kind)
        if team:
            stmt = stmt.where(AgentRegistry.team == team)
        return list((await s.execute(stmt)).scalars())


async def _wake(kind: str, team: str | None, text: str) -> None:
    for name in await _bots(kind, team):
        try:
            await trigger_bot(name, text)
        except GatewayError as exc:
            log.warning("could not wake %s: %s", name, exc)
            async with system_session() as s:
                row = await s.get(AgentRegistry, name)
                if row:
                    row.status, row.last_error = "error", str(exc)[:500]


# ------------------------------------------------------------------ shared teams

async def wake_watchers(team: str) -> None:
    await _wake("watcher", team, "[SCHEDULER] Run your watch cycle now: fetch fresh data for every symbol in your "
                                 "watchlist and emit signals only where something meaningful changed.")


async def wake_researchers() -> None:
    await _wake("researcher", None, "[SCHEDULER] Run your research cycle: gather today's credible news and data "
                                    "for your asset class and save a research note.")


async def wake_analysts() -> None:
    await _wake("analyst", None, "[SCHEDULER] Run your analysis: read the latest research and signals for your "
                                 "asset class, then save an expert analysis note. Also resolve open coverage "
                                 "requests by assigning symbols to the right cluster.")


async def wake_deal_scout() -> None:
    async with system_session() as s:
        pending = await s.scalar(select(func.count()).select_from(Merchant)
                                 .where(Merchant.sources_status.in_(["pending", "failed"])))
    if pending:
        await _wake("deals_scout", None, f"[SCHEDULER] {pending} merchants need sources. Find official websites, "
                                         "deal pages and social media accounts for the next batch.")


async def wake_deal_crawler() -> None:
    await _wake("deals_crawler", None, "[SCHEDULER] Crawl the next batch of merchants and Pakistani bank discount "
                                       "pages for current deals and save them.")


async def wake_deal_curator() -> None:
    await _wake("deals_curator", None, "[SCHEDULER] Curate the deals database: expire past deals, remove "
                                       "duplicates and re-check low-confidence deals.")


# ------------------------------------------------------------------ users

async def _active_users() -> list[tuple]:
    async with system_session() as s:
        return (await s.execute(
            select(User.id, User.full_name, UserProfile)
            .join(UserProfile, UserProfile.user_id == User.id)
            .where(User.is_active.is_(True), User.onboarding_completed.is_(True))
        )).all()


async def weekly_motivation() -> None:
    """'Great! you just saved x amount this week.'"""
    for user_id, name, _ in await _active_users():
        async with scoped_session(user_id, "user") as s:
            saved = await s.scalar(select(func.coalesce(func.sum(SavingsEntry.amount), 0)).where(
                SavingsEntry.created_at >= datetime.now(UTC) - timedelta(days=7), SavingsEntry.amount > 0))
        first = (name or "").split(" ")[0]
        if saved and saved > 0:
            await notify(user_id, "motivation", f"Great job{', ' + first if first else ''}! 🌱",
                         f"You saved Rs. {float(saved):,.0f} this week. Keep it up!")
        else:
            await notify(user_id, "motivation", "A small step this week?",
                         "Even Rs. 500 towards a goal adds up. Ask me for a quick saving tip!",
                         url="/dashboard?chat=1")


async def weekly_review() -> None:
    """The assistant reaches out on its own; replies arrive as push notifications if the app is closed."""
    for user_id, _, _ in await _active_users():
        async with system_session() as s:
            ready = await s.scalar(select(ChatRoom.status).where(ChatRoom.user_id == user_id))
        if ready != "ready":
            continue
        try:
            await send_to_room(user_id, "[SCHEDULER] Weekly check-in: review this week's spending vs. their goals "
                                        "and send ONE short, encouraging message with one concrete tip and one "
                                        "relevant deal if any. Do not ask more than one question.")
        except GatewayError as exc:
            log.warning("weekly review for %s failed: %s", user_id, exc)


async def sadqah_reminders(frequency: str) -> None:
    for user_id, _, profile in await _active_users():
        if not profile.sadqah_opt_in or (profile.sadqah_frequency or "friday") != frequency:
            continue
        amount = None
        if profile.sadqah_mode == "percent_income" and profile.monthly_income and profile.sadqah_value:
            monthly = Decimal(profile.monthly_income) * Decimal(profile.sadqah_value) / 100
            amount = monthly / (4 if frequency in ("weekly", "friday") else 1)
        elif profile.sadqah_value:
            amount = Decimal(profile.sadqah_value)
        body = (f"Your planned sadqah: Rs. {float(amount):,.0f}. " if amount else "") + \
            "“Charity does not decrease wealth.” Tap if you'd like ideas on where to give."
        await notify(user_id, "sadqah", "Sadqah reminder 🤲", body, url="/dashboard?chat=1")


async def month_end_leftover() -> None:
    """For people who save 'whatever is left', move the month's unspent income into goals."""
    today = date.today()
    if (today + timedelta(days=1)).month == today.month:
        return  # not the last day of the month
    month_start = datetime(today.year, today.month, 1, tzinfo=UTC)
    for user_id, _, profile in await _active_users():
        if profile.savings_mode != "leftover":
            continue
        async with scoped_session(user_id, "user") as s:
            income = await s.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.is_income.is_(True), Transaction.occurred_at >= month_start))
            spent = await s.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.direction == "debit", Transaction.occurred_at >= month_start,
                Transaction.category_slug != "transfer"))
            left = finance.money(income) - finance.money(spent)
            if left <= 0:
                continue
            from app.models import Goal

            goals = list((await s.execute(select(Goal).where(Goal.status == "active"))).scalars())
            allocs = finance.split_savings(left, goals, profile.goal_split_mode)
            await finance.add_savings(s, user_id, allocs, "allocation", "Month-end leftover")
        await notify(user_id, "motivation", "Month closed 🎯", f"Rs. {float(left):,.0f} you didn't spend moved to savings.")


async def overspend_nudge() -> None:
    """Evening nudge when today's spending is well above the person's daily budget."""
    since = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    for user_id, _, profile in await _active_users():
        if not profile.monthly_income:
            continue
        budget = Decimal(profile.monthly_income) * Decimal("0.7") / 30
        async with scoped_session(user_id, "user") as s:
            spent = await s.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.direction == "debit", Transaction.occurred_at >= since,
                Transaction.category_slug.notin_(["transfer", "housing", "utilities", "education"])))
        if spent and spent > budget * Decimal("1.8"):
            await notify(user_id, "motivation", "Heads up on today's spending",
                         f"You've spent Rs. {float(spent):,.0f} today, above your usual daily budget. "
                         "Want a quick plan to balance the week?", url="/dashboard?chat=1")
