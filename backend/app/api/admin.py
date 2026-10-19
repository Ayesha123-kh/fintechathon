import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import enforce
from app.core.deps import Principal, admin_db, require_admin
from app.core.security import revoke_all_sessions
from app.models import (
    AgentRegistry,
    AuditLog,
    Bank,
    BankAccount,
    Card,
    CardProduct,
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
    UserFollow,
    WatchCluster,
)
from app.services.omb import GatewayError, deprovision_user, gateway_status, gateway_usage, resync_agents

router = APIRouter(prefix="/admin", tags=["admin"])


async def audit(s: AsyncSession, actor: Principal, action: str, target: str, data: dict | None = None) -> None:
    s.add(AuditLog(actor_id=actor.user_id, action=action, target=target, data=data or {}))


@router.get("/stats")
async def stats(s: AsyncSession = Depends(admin_db)) -> dict:
    day = datetime.now(UTC) - timedelta(days=1)
    is_user = User.role == "user"  # admin accounts are not counted as users
    return {
        "users": await s.scalar(select(func.count()).select_from(User).where(is_user)),
        "active_24h": await s.scalar(select(func.count()).select_from(User).where(is_user, User.last_login_at >= day)),
        "onboarded": await s.scalar(select(func.count()).select_from(User)
                                    .where(is_user, User.onboarding_completed.is_(True))),
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
    stmt = select(User, ChatRoom.status).outerjoin(ChatRoom, ChatRoom.user_id == User.id).where(User.role == "user")
    if q:
        stmt = stmt.where(or_(User.email.ilike(f"%{q}%"), User.full_name.ilike(f"%{q}%")))
    total = await s.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await s.execute(stmt.order_by(User.created_at.desc()).limit(min(limit, 200)).offset(offset))).all()
    return {"total": total, "users": [
        {"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": u.role, "is_active": u.is_active,
         "onboarding_completed": u.onboarding_completed, "created_at": u.created_at,
         "last_login_at": u.last_login_at, "assistant": room_status or "none"} for u, room_status in rows]}


class UserPatch(BaseModel):
    is_active: bool | None = None


@router.patch("/users/{user_id}")
async def update_user(user_id: uuid.UUID, body: UserPatch, actor: Principal = Depends(require_admin),
                      s: AsyncSession = Depends(admin_db)) -> dict:
    user = await s.get(User, user_id)
    if not user or user.role != "user":
        raise HTTPException(404, "not_found")
    if body.is_active is not None and body.is_active != user.is_active:
        user.is_active = body.is_active
        if not body.is_active:
            await revoke_all_sessions(user.id)
    await audit(s, actor, "user.update", str(user_id), body.model_dump(exclude_none=True))
    return {"ok": True}


@router.delete("/users/{user_id}")
async def delete_user(user_id: uuid.UUID, actor: Principal = Depends(require_admin),
                      s: AsyncSession = Depends(admin_db)) -> dict:
    """Permanently delete an account, all its data (cascade) and its OpenMausBot team."""
    if user_id == actor.user_id:
        raise HTTPException(400, "cannot_delete_yourself")
    user = await s.get(User, user_id)
    if not user or user.role != "user":
        raise HTTPException(404, "not_found")
    omb_cleanup = "done"
    try:
        await deprovision_user(user_id)
    except GatewayError as exc:
        # The gateway also removes orphaned teams on every sync, so this is retried automatically.
        omb_cleanup = f"deferred: {exc}"[:200]
    await revoke_all_sessions(user_id)
    await audit(s, actor, "user.delete", str(user_id), {"email": user.email, "omb_cleanup": omb_cleanup})
    await s.delete(user)
    return {"ok": True, "omb_cleanup": omb_cleanup}


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
    await enforce(f"agents-sync:{actor.user_id}", 5, 600)  # a full re-apply of every team
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


# ------------------------------------------------------------------ reference data (read-only views)

@router.get("/banks")
async def banks(s: AsyncSession = Depends(admin_db)) -> list[dict]:
    """Every supported bank and wallet with how much of the app touches it."""
    rows = (await s.execute(select(Bank).order_by(Bank.kind, Bank.name))).scalars().all()
    products = {(b, t): n for b, t, n in (await s.execute(
        select(CardProduct.bank_id, CardProduct.card_type, func.count()).group_by(CardProduct.bank_id, CardProduct.card_type)))}
    accounts = dict((await s.execute(select(BankAccount.bank_id, func.count()).group_by(BankAccount.bank_id))).all())
    cards = dict((await s.execute(select(Card.bank_id, func.count()).group_by(Card.bank_id))).all())
    deals_by_bank = dict((await s.execute(select(Deal.bank_id, func.count()).where(
        Deal.status == "active", Deal.bank_id.is_not(None)).group_by(Deal.bank_id))).all())
    return [{
        "id": str(b.id), "name": b.name, "short_name": b.short_name, "kind": b.kind, "website": b.website,
        "email_domains": b.email_domains, "aliases": b.aliases,
        "debit_products": products.get((b.id, "debit"), 0), "credit_products": products.get((b.id, "credit"), 0),
        "user_accounts": accounts.get(b.id, 0), "user_cards": cards.get(b.id, 0),
        "active_deals": deals_by_bank.get(b.id, 0),
    } for b in rows]


@router.get("/cards")
async def card_catalog(q: str | None = None, bank: str | None = None, card_type: str | None = None,
                       confidence: str | None = None, limit: int = 500, s: AsyncSession = Depends(admin_db)) -> dict:
    """The card catalog (app/seed/cards.py) with how many users hold a matching card."""
    stmt = select(CardProduct, Bank.name, Bank.short_name).join(Bank, Bank.id == CardProduct.bank_id)
    if q:
        stmt = stmt.where(or_(CardProduct.name.ilike(f"%{q}%"), Bank.name.ilike(f"%{q}%")))
    if bank:
        stmt = stmt.where(Bank.short_name == bank)
    if card_type in ("debit", "credit"):
        stmt = stmt.where(CardProduct.card_type == card_type)
    if confidence:
        stmt = stmt.where(CardProduct.confidence == confidence)
    rows = (await s.execute(stmt.order_by(Bank.name, CardProduct.card_type, CardProduct.name).limit(min(limit, 1000)))).all()
    held: dict[tuple, int] = {}
    for bank_id, network, tier, ctype, n in (await s.execute(
            select(Card.bank_id, Card.network, Card.tier, Card.card_type, func.count())
            .group_by(Card.bank_id, Card.network, Card.tier, Card.card_type))).all():
        held[(bank_id, network, tier, ctype)] = n

    def held_by(p: CardProduct) -> int:
        # A product with no stated network matches a user's card of any network.
        return sum(n for (b, net, tier, ctype), n in held.items()
                   if b == p.bank_id and ctype == p.card_type and (p.network is None or net == p.network)
                   and (p.tier is None or (tier or "") == p.tier))

    by_conf = dict((await s.execute(select(CardProduct.confidence, func.count()).group_by(CardProduct.confidence))).all())
    return {"total": await s.scalar(select(func.count()).select_from(CardProduct)), "by_confidence": by_conf,
            "cards": [{"id": str(p.id), "name": p.name, "bank": bank_name, "bank_short": short, "network": p.network,
                       "tier": p.tier, "card_type": p.card_type, "islamic": p.is_islamic, "confidence": p.confidence,
                       "source_url": p.source_url, "verified_on": p.verified_on, "held_by_users": held_by(p)}
                      for p, bank_name, short in rows]}


@router.get("/companies")
async def companies(q: str | None = None, status: str | None = None, category: str | None = None,
                    limit: int = 50, offset: int = 0, s: AsyncSession = Depends(admin_db)) -> dict:
    """The merchant directory (businesses the deal bots look up), with how many live deals each has."""
    live_deals = (select(Deal.merchant_id, func.count().label("n")).where(Deal.status == "active")
                  .group_by(Deal.merchant_id).subquery())
    stmt = select(Merchant, func.coalesce(live_deals.c.n, 0)).outerjoin(live_deals, live_deals.c.merchant_id == Merchant.id)
    if q:
        stmt = stmt.where(or_(Merchant.name.ilike(f"%{q}%"), Merchant.subcategory.ilike(f"%{q}%")))
    if status:
        stmt = stmt.where(Merchant.sources_status == status)
    if category:
        stmt = stmt.where(Merchant.category_slug == category)
    total = await s.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = (await s.execute(stmt.order_by(Merchant.seen_in_transactions.desc(), Merchant.name)
                            .limit(min(limit, 200)).offset(offset))).all()
    by_status = dict((await s.execute(select(Merchant.sources_status, func.count()).group_by(Merchant.sources_status))).all())
    return {"total": total, "by_status": by_status, "companies": [{
        "id": str(m.id), "name": m.name, "category": m.category_slug, "subcategory": m.subcategory,
        "website": m.website, "sources": sorted((m.sources or {}).keys()), "status": m.sources_status,
        "seen_in_transactions": m.seen_in_transactions, "last_crawled_at": m.last_crawled_at, "live_deals": n,
    } for m, n in rows]}


@router.get("/assets")
async def tracked_assets(s: AsyncSession = Depends(admin_db)) -> dict:
    """Every symbol the watcher bots track, with the cluster it sits in, who follows it and its latest signal."""
    clusters = (await s.execute(select(WatchCluster).order_by(WatchCluster.asset_class, WatchCluster.name))).scalars().all()
    followers = {(a, sym): n for a, sym, n in (await s.execute(
        select(UserFollow.asset_class, UserFollow.symbol, func.count()).group_by(UserFollow.asset_class, UserFollow.symbol)))}
    latest = {(m.asset_class, m.symbol): m for m in (await s.execute(
        select(MarketSignal).distinct(MarketSignal.asset_class, MarketSignal.symbol)
        .order_by(MarketSignal.asset_class, MarketSignal.symbol, MarketSignal.created_at.desc()))).scalars()}
    week = datetime.now(UTC) - timedelta(days=7)
    recent = {(a, sym): n for a, sym, n in (await s.execute(
        select(MarketSignal.asset_class, MarketSignal.symbol, func.count())
        .where(MarketSignal.created_at >= week).group_by(MarketSignal.asset_class, MarketSignal.symbol)))}
    assets = []
    for c in clusters:
        for sym in c.symbols or []:
            sig = latest.get((c.asset_class, sym))
            assets.append({
                "symbol": sym, "asset_class": c.asset_class, "cluster": c.name, "cluster_slug": c.slug,
                "active": c.active, "followers": followers.get((c.asset_class, sym), 0),
                "signals_7d": recent.get((c.asset_class, sym), 0),
                "last_signal": sig.signal if sig else None, "last_signal_at": sig.created_at if sig else None,
                "last_price": float(sig.price) if sig and sig.price is not None else None,
            })
    by_class: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
    return {"total": len(assets), "by_asset_class": by_class, "assets": assets}
