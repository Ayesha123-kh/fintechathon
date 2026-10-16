"""Read APIs behind the dashboard, goal details and bank details screens.

Changes are made by talking to the assistant (chat-first app); these screens only read,
except a few toggles that also exist in chat.
"""

import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import Principal, current_principal, own_db
from app.models import (
    Bank,
    Card,
    ChatRoom,
    EmailConnection,
    Goal,
    Notification,
    SavingsEntry,
    Transaction,
    User,
    UserProfile,
)
from app.services import finance
from app.services.deals import find_deals
from app.services.omb import refresh_room

router = APIRouter(tags=["finance"])


@router.get("/me")
async def me(p: Principal = Depends(current_principal), s: AsyncSession = Depends(own_db)) -> dict:
    user = await s.get(User, p.user_id)
    profile = await s.get(UserProfile, p.user_id)
    room = await s.get(ChatRoom, p.user_id)
    return {
        "id": str(user.id), "email": user.email, "full_name": user.full_name, "role": user.role,
        "onboarding_completed": user.onboarding_completed,
        "language": profile.language if profile else "en",
        "investment_opt_in": bool(profile and profile.investment_opt_in),
        "assistant_status": room.status if room else "pending",
        "test_tools": settings.test_tools_enabled,
    }


class MePatch(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    language: str | None = None


@router.patch("/me")
async def update_me(body: MePatch, p: Principal = Depends(current_principal),
                    s: AsyncSession = Depends(own_db)) -> dict:
    user = await s.get(User, p.user_id)
    profile = await s.get(UserProfile, p.user_id)
    if body.full_name:
        user.full_name = body.full_name
    if body.language in ("en", "ur", "roman_ur"):
        profile.language = body.language
    await s.flush()
    await refresh_room(p.user_id)
    return {"ok": True}


@router.get("/dashboard")
async def get_dashboard(p: Principal = Depends(current_principal), s: AsyncSession = Depends(own_db)) -> dict:
    data = await finance.dashboard(s, p.user_id)
    data["deals_for_you"] = await find_deals(s, p.user_id, limit=6)
    data["unread_notifications"] = await s.scalar(
        select(func.count()).select_from(Notification).where(Notification.read_at.is_(None)))
    data["email_connected"] = bool(await s.scalar(
        select(func.count()).select_from(EmailConnection).where(EmailConnection.status == "active")))
    return data


@router.get("/goals")
async def list_goals(s: AsyncSession = Depends(own_db)) -> list[dict]:
    goals = (await s.execute(select(Goal).where(Goal.status != "cancelled").order_by(Goal.created_at))).scalars()
    return [_goal_out(g) for g in goals]


def _goal_out(g: Goal) -> dict:
    remaining = max(finance.money(g.target_amount) - finance.money(g.saved_amount), 0)
    months = finance._months_left(g.deadline, date.today())
    return {
        "id": str(g.id), "name": g.name, "icon": g.icon, "status": g.status, "priority": g.priority,
        "weight": g.weight, "target": g.target_amount, "saved": g.saved_amount, "remaining": remaining,
        "deadline": g.deadline, "notes": g.notes, "created_at": g.created_at,
        "progress": float(min(1, finance.money(g.saved_amount) / finance.money(g.target_amount))) if g.target_amount else 0,
        "monthly_needed": finance.money(remaining / months) if remaining else 0,
    }


@router.get("/goals/{goal_id}")
async def goal_detail(goal_id: uuid.UUID, s: AsyncSession = Depends(own_db)) -> dict:
    g = await s.get(Goal, goal_id)
    if not g:
        raise HTTPException(404, "not_found")
    entries = (await s.execute(select(SavingsEntry).where(SavingsEntry.goal_id == goal_id)
                               .order_by(SavingsEntry.created_at.desc()).limit(100))).scalars().all()
    # Average monthly contribution over the last 90 days -> projected completion date.
    since = datetime.now(UTC) - timedelta(days=90)
    recent = sum((e.amount for e in entries if e.created_at >= since and e.amount > 0), 0)
    monthly_rate = finance.money(recent / 3) if recent else 0
    out = _goal_out(g)
    remaining = out["remaining"]
    projected = None
    if monthly_rate and remaining:
        projected = (date.today() + timedelta(days=int(float(remaining / monthly_rate) * 30.4))).isoformat()
    out.update({
        "monthly_rate": monthly_rate, "projected_completion": projected,
        "on_track": (projected is None and remaining == 0) or (bool(projected) and (not g.deadline or projected <= g.deadline.isoformat())),
        "history": [{"id": str(e.id), "amount": e.amount, "source": e.source, "note": e.note,
                     "created_at": e.created_at} for e in entries],
    })
    return out


@router.get("/banks")
async def bank_details(p: Principal = Depends(current_principal), s: AsyncSession = Depends(own_db)) -> dict:
    data = await finance.dashboard(s, p.user_id)
    cards = (await s.execute(select(Card, Bank.name).join(Bank, Bank.id == Card.bank_id))).all()
    accounts = []
    for row in data["banks"]:
        acc_id = uuid.UUID(row["account_id"])
        txs = (await s.execute(select(Transaction).where(Transaction.account_id == acc_id)
                               .order_by(Transaction.occurred_at.desc()).limit(20))).scalars()
        accounts.append({**row,
                         "cards": [{"id": str(c.id), "label": c.label, "network": c.network, "tier": c.tier,
                                    "type": c.card_type}
                                   for c, _ in cards if c.account_id == acc_id],
                         "transactions": [{"id": str(t.id), "occurred_at": t.occurred_at, "amount": t.amount,
                                           "direction": t.direction, "merchant": t.merchant_raw,
                                           "category": t.category_slug} for t in txs]})
    unlinked = [{"id": str(c.id), "label": c.label, "bank": bank, "network": c.network, "tier": c.tier,
                 "type": c.card_type} for c, bank in cards if c.account_id is None]
    return {"total_balance": data["total_balance"], "total_savings": data["total_savings"],
            "expendable": data["expendable"], "accounts": accounts, "other_cards": unlinked}


@router.get("/transactions")
async def transactions(days: int = 30, category: str | None = None, account_id: uuid.UUID | None = None,
                       limit: int = 50, s: AsyncSession = Depends(own_db)) -> list[dict]:
    stmt = select(Transaction).where(Transaction.occurred_at >= datetime.now(UTC) - timedelta(days=days))
    if category:
        stmt = stmt.where(Transaction.category_slug == category)
    if account_id:
        stmt = stmt.where(Transaction.account_id == account_id)
    rows = (await s.execute(stmt.order_by(Transaction.occurred_at.desc()).limit(min(limit, 200)))).scalars()
    return [{"id": str(t.id), "occurred_at": t.occurred_at, "amount": t.amount, "direction": t.direction,
             "merchant": t.merchant_raw, "category": t.category_slug, "source": t.source} for t in rows]


@router.get("/deals")
async def deals(category: str | None = None, q: str | None = None, p: Principal = Depends(current_principal),
                s: AsyncSession = Depends(own_db)) -> list[dict]:
    return await find_deals(s, p.user_id, category=category, query=q, limit=30)


@router.get("/notifications")
async def notifications(s: AsyncSession = Depends(own_db)) -> list[dict]:
    rows = (await s.execute(select(Notification).order_by(Notification.created_at.desc()).limit(50))).scalars()
    return [{"id": str(n.id), "kind": n.kind, "title": n.title, "body": n.body, "url": n.url,
             "read": n.read_at is not None, "created_at": n.created_at} for n in rows]


@router.post("/notifications/read")
async def notifications_read(s: AsyncSession = Depends(own_db)) -> dict:
    for n in (await s.execute(select(Notification).where(Notification.read_at.is_(None)))).scalars():
        n.read_at = datetime.now(UTC)
    return {"ok": True}
