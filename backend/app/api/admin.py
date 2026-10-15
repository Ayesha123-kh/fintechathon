import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Principal, admin_db, require_admin
from app.core.security import revoke_all_sessions, update_session_role
from app.models import (
    AgentRegistry,
    AuditLog,
    ChatRoom,
    CoverageRequest,
    Deal,
    EmailConnection,
    MarketSignal,
    Merchant,
    Plan,
    ResearchNote,
    Subscription,
    Transaction,
    User,
    WatchCluster,
)
from app.services.omb import GatewayError, gateway_status, gateway_usage, resync_agents

router = APIRouter(prefix="/admin", tags=["admin"])


async def audit(s: AsyncSession, actor: Principal, action: str, target: str, data: dict | None = None) -> None:
    s.add(AuditLog(actor_id=actor.user_id, action=action, target=target, data=data or {}))


@router.get("/stats")
async def stats(s: AsyncSession = Depends(admin_db)) -> dict:
    day = datetime.now(UTC) - timedelta(days=1)
    return {
        "users": await s.scalar(select(func.count()).select_from(User)),
        "active_24h": await s.scalar(select(func.count()).select_from(User).where(User.last_login_at >= day)),
        "onboarded": await s.scalar(select(func.count()).select_from(User).where(User.onboarding_completed.is_(True))),
        "rooms_ready": await s.scalar(select(func.count()).select_from(ChatRoom).where(ChatRoom.status == "ready")),
        "rooms_error": await s.scalar(select(func.count()).select_from(ChatRoom).where(ChatRoom.status == "error")),
        "email_connections": await s.scalar(select(func.count()).select_from(EmailConnection)),
        "transactions_24h": await s.scalar(select(func.count()).select_from(Transaction)
                                           .where(Transaction.created_at >= day)),
        "deals_active": await s.scalar(select(func.count()).select_from(Deal).where(Deal.status == "active")),
        "deals_review": await s.scalar(select(func.count()).select_from(Deal).where(Deal.status == "pending_review")),
        "merchants": await s.scalar(select(func.count()).select_from(Merchant)),
        "signals_24h": await s.scalar(select(func.count()).select_from(MarketSignal)
                                      .where(MarketSignal.created_at >= day)),
        "research_24h": await s.scalar(select(func.count()).select_from(ResearchNote)
                                       .where(ResearchNote.created_at >= day)),
        "coverage_open": await s.scalar(select(func.count()).select_from(CoverageRequest)
                                        .where(CoverageRequest.status == "open")),
    }


@router.get("/users")
async def users(q: str | None = None, limit: int = 50, offset: int = 0, s: AsyncSession = Depends(admin_db)) -> dict:
    stmt = select(User, ChatRoom.status).outerjoin(ChatRoom, ChatRoom.user_id == User.id)
    if q:
        stmt = stmt.where(or_(User.email.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%")))
    total = await s.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await s.execute(stmt.order_by(User.created_at.desc()).limit(min(limit, 200)).offset(offset))).all()
    return {"total": total, "users": [
        {"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": u.role, "is_active": u.is_active,
         "onboarding_completed": u.onboarding_completed, "created_at": u.created_at,
         "last_login_at": u.last_login_at, "assistant": room_status or "none"} for u, room_status in rows]}


class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None


@router.patch("/users/{user_id}")
async def update_user(user_id: uuid.UUID, body: UserPatch, actor: Principal = Depends(require_admin),
                      s: AsyncSession = Depends(admin_db)) -> dict:
    user = await s.get(User, user_id)
    if not user:
        raise HTTPException(404, "not_found")
    if user.id == actor.user_id and (body.role == "user" or body.is_active is False):
        raise HTTPException(400, "cannot_demote_or_disable_yourself")
    if body.role in ("user", "admin") and body.role != user.role:
        user.role = body.role
        await update_session_role(user.id, body.role)
    if body.is_active is not None and body.is_active != user.is_active:
        user.is_active = body.is_active
        if not body.is_active:
            await revoke_all_sessions(user.id)
    await audit(s, actor, "user.update", str(user_id), body.model_dump(exclude_none=True))
    return {"ok": True}


@router.get("/agents")
async def agents(s: AsyncSession = Depends(admin_db)) -> dict:
    rows = (await s.execute(select(AgentRegistry).order_by(AgentRegistry.team, AgentRegistry.name))).scalars()
    try:
        gateway = await gateway_status()
    except GatewayError as exc:
        gateway = {"ok": False, "error": str(exc)}
    return {"gateway": gateway, "agents": [
        {"name": a.name, "team": a.team, "kind": a.kind, "status": a.status, "omb_bot_id": a.omb_bot_id,
         "soul_hash": (a.soul_hash or "")[:10], "last_run_at": a.last_run_at, "updated_at": a.updated_at,
         "last_error": a.last_error} for a in rows]}


@router.post("/agents/sync")
async def agents_sync(actor: Principal = Depends(require_admin), s: AsyncSession = Depends(admin_db)) -> dict:
    await audit(s, actor, "agents.sync", "")
    try:
        return await resync_agents()
    except GatewayError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/usage")
async def usage(_: Principal = Depends(require_admin)) -> dict:
    try:
        return await gateway_usage()
    except GatewayError as exc:
        return {"error": str(exc)}


@router.get("/deals")
async def deals(status: str | None = None, q: str | None = None, limit: int = 100,
                s: AsyncSession = Depends(admin_db)) -> list[dict]:
    stmt = select(Deal)
    if status:
        stmt = stmt.where(Deal.status == status)
    if q:
        stmt = stmt.where(or_(Deal.title.ilike(f"%{q}%"), Deal.merchant_name.ilike(f"%{q}%")))
    rows = (await s.execute(stmt.order_by(Deal.updated_at.desc()).limit(min(limit, 300)))).scalars()
    return [{"id": str(d.id), "merchant": d.merchant_name, "title": d.title, "category": d.category_slug,
             "deal_type": d.deal_type, "discount_type": d.discount_type, "discount_value": d.discount_value,
             "requires_card": d.requires_card, "card_network": d.card_network, "card_tier": d.card_tier,
             "valid_until": d.valid_until, "status": d.status, "verified": d.verified_by_admin,
             "confidence": d.confidence, "source_url": d.source_url, "updated_at": d.updated_at} for d in rows]


class DealPatch(BaseModel):
    status: str | None = None
    verified: bool | None = None


@router.patch("/deals/{deal_id}")
async def update_deal(deal_id: uuid.UUID, body: DealPatch, actor: Principal = Depends(require_admin),
                      s: AsyncSession = Depends(admin_db)) -> dict:
    deal = await s.get(Deal, deal_id)
    if not deal:
        raise HTTPException(404, "not_found")
    if body.status in ("active", "expired", "pending_review", "rejected"):
        deal.status = body.status
    if body.verified is not None:
        deal.verified_by_admin = body.verified
    await audit(s, actor, "deal.update", str(deal_id), body.model_dump(exclude_none=True))
    return {"ok": True}


@router.delete("/deals/{deal_id}")
async def delete_deal(deal_id: uuid.UUID, actor: Principal = Depends(require_admin),
                      s: AsyncSession = Depends(admin_db)) -> dict:
    deal = await s.get(Deal, deal_id)
    if deal:
        await s.delete(deal)
        await audit(s, actor, "deal.delete", str(deal_id))
    return {"ok": True}


@router.get("/clusters")
async def clusters(s: AsyncSession = Depends(admin_db)) -> dict:
    rows = (await s.execute(select(WatchCluster).order_by(WatchCluster.asset_class, WatchCluster.name))).scalars()
    reqs = (await s.execute(select(CoverageRequest.asset_class, CoverageRequest.symbol, func.count())
                            .where(CoverageRequest.status == "open")
                            .group_by(CoverageRequest.asset_class, CoverageRequest.symbol))).all()
    return {
        "clusters": [{"id": str(c.id), "slug": c.slug, "asset_class": c.asset_class, "name": c.name,
                      "symbols": c.symbols, "active": c.active} for c in rows],
        "coverage_requests": [{"asset_class": a, "symbol": sym, "requests": n} for a, sym, n in reqs],
    }


class ClusterIn(BaseModel):
    asset_class: str
    slug: str
    name: str
    description: str = ""
    symbols: list[str] = []


@router.post("/clusters")
async def create_cluster(body: ClusterIn, actor: Principal = Depends(require_admin),
                         s: AsyncSession = Depends(admin_db)) -> dict:
    """A new cluster gets its own watcher bot on the next agent sync."""
    s.add(WatchCluster(**body.model_dump() | {"symbols": [x.upper() for x in body.symbols]}))
    await audit(s, actor, "cluster.create", body.slug)
    return {"ok": True}


class ClusterPatch(BaseModel):
    symbols: list[str] | None = None
    active: bool | None = None


@router.patch("/clusters/{cluster_id}")
async def update_cluster(cluster_id: uuid.UUID, body: ClusterPatch, actor: Principal = Depends(require_admin),
                         s: AsyncSession = Depends(admin_db)) -> dict:
    c = await s.get(WatchCluster, cluster_id)
    if not c:
        raise HTTPException(404, "not_found")
    if body.symbols is not None:
        c.symbols = [x.upper().strip() for x in body.symbols if x.strip()]
    if body.active is not None:
        c.active = body.active
    await audit(s, actor, "cluster.update", c.slug, body.model_dump(exclude_none=True))
    return {"ok": True}


@router.get("/plans")
async def plans(s: AsyncSession = Depends(admin_db)) -> list[dict]:
    rows = (await s.execute(select(Plan).order_by(Plan.price_monthly))).scalars()
    out = []
    for p in rows:
        subs = await s.scalar(select(func.count()).select_from(Subscription).where(
            Subscription.plan_id == p.id, Subscription.status == "active"))
        out.append({"id": str(p.id), "code": p.code, "name": p.name, "price_monthly": p.price_monthly,
                    "currency": p.currency, "features": p.features, "is_active": p.is_active, "subscribers": subs})
    return out


class PlanIn(BaseModel):
    code: str
    name: str
    price_monthly: float = 0
    features: dict = {}
    is_active: bool = True


@router.post("/plans")
async def upsert_plan(body: PlanIn, actor: Principal = Depends(require_admin),
                      s: AsyncSession = Depends(admin_db)) -> dict:
    plan = await s.scalar(select(Plan).where(Plan.code == body.code))
    if plan:
        for k, v in body.model_dump().items():
            setattr(plan, k, v)
    else:
        s.add(Plan(**body.model_dump()))
    await audit(s, actor, "plan.upsert", body.code)
    return {"ok": True}


@router.get("/audit")
async def audit_log(s: AsyncSession = Depends(admin_db)) -> list[dict]:
    rows = (await s.execute(select(AuditLog, User.email).outerjoin(User, User.id == AuditLog.actor_id)
                            .order_by(AuditLog.created_at.desc()).limit(100))).all()
    return [{"action": a.action, "target": a.target, "data": a.data, "actor": email, "at": a.created_at}
            for a, email in rows]
