"""`fin_market` MCP server: tools for the shared teams (researchers, analysts, watchers, deal crawlers).

These bots never see user data. They read public sources and write global tables
(signals, research notes, merchants, deals) through a 'system' scoped session.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.core.db import system_session
from app.mcp.common import out
from app.models import (
    AgentRegistry,
    Bank,
    CoverageRequest,
    Deal,
    MarketSignal,
    Merchant,
    ResearchNote,
    WatchCluster,
)
from app.services import market_data
from app.services.deals import deal_fingerprint
from app.services.text import normalize_name

mcp = FastMCP(
    "fin_market",
    instructions="Public market data, web research and the shared deals/signals database for Pakistan.",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

ASSET_CLASSES = Literal["gold_silver", "psx", "foreign_stocks", "crypto", "pk_real_estate"]


async def _mark_run(bot_name: str) -> None:
    if not bot_name:
        return
    async with system_session() as s:
        await s.execute(update(AgentRegistry).where(AgentRegistry.name == bot_name)
                        .values(last_run_at=datetime.now(UTC), status="ok"))


# ------------------------------------------------------------------ web

@mcp.tool()
async def web_search(query: str, news: bool = False, max_results: int = 8) -> list[dict]:
    """Search the web (DuckDuckGo, Pakistan region). news=true for recent news articles."""
    return await market_data.web_search(query, max_results=min(max_results, 15), news=news)


@mcp.tool()
async def fetch_url(url: str) -> dict:
    """Read a web page as text (also lists links that look like deals/offers/social profiles)."""
    return await market_data.fetch_url(url)


# ------------------------------------------------------------------ market data

@mcp.tool()
async def fx_rates() -> dict:
    """USD based exchange rates incl. PKR."""
    return await market_data.fx_rates("USD")


@mcp.tool()
async def metal_price(symbol: Literal["XAU", "XAG", "GOLD_TOLA_PK", "SILVER_TOLA_PK"]) -> dict:
    """Gold/silver spot (USD/oz) and Pakistani per-tola spot equivalent in PKR."""
    return await market_data.metal_price(symbol)


@mcp.tool()
async def crypto_prices(symbols: list[str]) -> dict:
    """Crypto prices in USD and PKR with 24h change, e.g. ['BTC','ETH']."""
    return await market_data.crypto_prices(symbols)


@mcp.tool()
async def psx_quote(symbol: str) -> dict:
    """Today's PSX price action for a ticker (e.g. OGDC, MEBL, LUCK)."""
    return await market_data.psx_quote(symbol)


@mcp.tool()
async def psx_history(symbol: str) -> dict:
    """Last ~60 daily closes for a PSX ticker."""
    return await market_data.psx_history(symbol)


@mcp.tool()
async def global_quote(symbol: str, range: Literal["5d", "1mo", "3mo", "6mo", "1y"] = "1mo") -> dict:
    """Price and recent closes for a US/global stock or ETF (e.g. AAPL, NVDA, SPY)."""
    return await market_data.global_quote(symbol, range)


# ------------------------------------------------------------------ watchlists & signals

@mcp.tool()
async def list_clusters(asset_class: ASSET_CLASSES | None = None) -> list[dict]:
    """Watch clusters (groups of related assets, one watcher bot each)."""
    async with system_session() as s:
        stmt = select(WatchCluster).where(WatchCluster.active.is_(True))
        if asset_class:
            stmt = stmt.where(WatchCluster.asset_class == asset_class)
        return out([{"slug": c.slug, "asset_class": c.asset_class, "name": c.name, "description": c.description,
                     "symbols": c.symbols} for c in (await s.execute(stmt)).scalars()])


@mcp.tool()
async def get_watchlist(cluster_slug: str) -> dict:
    """The symbols a watcher must check this cycle."""
    async with system_session() as s:
        c = await s.scalar(select(WatchCluster).where(WatchCluster.slug == cluster_slug))
        if not c:
            return {"error": f"unknown cluster {cluster_slug}"}
        return {"cluster": c.slug, "asset_class": c.asset_class, "name": c.name, "symbols": c.symbols}


@mcp.tool()
async def emit_signal(
    bot_name: str,
    cluster_slug: str,
    symbol: str,
    signal: Literal["buy", "sell", "hold", "watch", "alert"],
    confidence: float,
    rationale: str,
    price: float | None = None,
    horizon: Literal["intraday", "swing", "long_term"] | None = None,
) -> dict:
    """Publish a signal for one asset. confidence 0..1. rationale: 1-3 sentences citing the data used.
    Only emit when something meaningful changed; otherwise skip."""
    async with system_session() as s:
        c = await s.scalar(select(WatchCluster).where(WatchCluster.slug == cluster_slug))
        if not c:
            return {"error": f"unknown cluster {cluster_slug}"}
        sig = MarketSignal(asset_class=c.asset_class, cluster_slug=c.slug, symbol=symbol.upper(), signal=signal,
                           confidence=max(0.0, min(1.0, confidence)), price=price, horizon=horizon,
                           rationale=rationale[:2000], created_by=bot_name[:120])
        s.add(sig)
        await s.flush()
        sid = str(sig.id)
    await _mark_run(bot_name)
    return {"ok": True, "signal_id": sid}


@mcp.tool()
async def recent_signals(asset_class: ASSET_CLASSES | None = None, symbol: str | None = None,
                         hours: int = 48) -> list[dict]:
    """Signals emitted recently (to avoid duplicates and for analysts)."""
    async with system_session() as s:
        stmt = select(MarketSignal).where(MarketSignal.created_at >= datetime.now(UTC) - timedelta(hours=hours))
        if asset_class:
            stmt = stmt.where(MarketSignal.asset_class == asset_class)
        if symbol:
            stmt = stmt.where(MarketSignal.symbol == symbol.upper())
        rows = (await s.execute(stmt.order_by(MarketSignal.created_at.desc()).limit(60))).scalars()
        return out([{"symbol": r.symbol, "signal": r.signal, "confidence": r.confidence, "price": r.price,
                     "rationale": r.rationale, "at": r.created_at, "by": r.created_by} for r in rows])


@mcp.tool()
async def save_research(
    bot_name: str,
    asset_class: ASSET_CLASSES,
    title: str,
    summary: str,
    sources: list[str],
    body: str = "",
    sentiment: Literal["bullish", "bearish", "neutral"] | None = None,
    symbols: list[str] | None = None,
    kind: Literal["research", "analysis"] = "research",
) -> dict:
    """Store a research or analysis note. sources must be URLs of credible sources you actually read."""
    if not sources and kind == "research":
        return {"ok": False, "error": "research needs at least one source URL"}
    async with system_session() as s:
        note = ResearchNote(asset_class=asset_class, kind=kind, title=title[:300], summary=summary[:3000],
                            body=body[:20000], sentiment=sentiment, symbols=[x.upper() for x in symbols or []],
                            sources=sources[:20], created_by=bot_name[:120])
        s.add(note)
    await _mark_run(bot_name)
    return {"ok": True}


@mcp.tool()
async def recent_research(asset_class: ASSET_CLASSES, days: int = 3) -> list[dict]:
    """Research and analysis notes from the last few days."""
    async with system_session() as s:
        rows = (await s.execute(select(ResearchNote).where(
            ResearchNote.asset_class == asset_class,
            ResearchNote.created_at >= datetime.now(UTC) - timedelta(days=days),
        ).order_by(ResearchNote.created_at.desc()).limit(20))).scalars()
        return out([{"kind": r.kind, "title": r.title, "summary": r.summary, "sentiment": r.sentiment,
                     "symbols": r.symbols, "sources": r.sources, "by": r.created_by, "at": r.created_at}
                    for r in rows])


@mcp.tool()
async def open_coverage_requests(asset_class: ASSET_CLASSES | None = None) -> list[dict]:
    """Assets users asked about that no watcher covers yet."""
    async with system_session() as s:
        stmt = select(CoverageRequest.asset_class, CoverageRequest.symbol).where(CoverageRequest.status == "open")
        if asset_class:
            stmt = stmt.where(CoverageRequest.asset_class == asset_class)
        rows = (await s.execute(stmt.distinct())).all()
        return [{"asset_class": a, "symbol": sym} for a, sym in rows]


@mcp.tool()
async def add_symbol_to_cluster(bot_name: str, cluster_slug: str, symbol: str) -> dict:
    """Assign a requested asset to the most fitting existing cluster (resolves coverage requests)."""
    symbol = symbol.upper().strip()
    async with system_session() as s:
        c = await s.scalar(select(WatchCluster).where(WatchCluster.slug == cluster_slug))
        if not c:
            return {"error": "unknown cluster"}
        if symbol not in c.symbols:
            c.symbols = [*c.symbols, symbol]
        await s.execute(update(CoverageRequest).where(
            CoverageRequest.symbol == symbol, CoverageRequest.asset_class == c.asset_class,
            CoverageRequest.status == "open").values(status="added", resolved_cluster=c.slug))
    await _mark_run(bot_name)
    return {"ok": True, "cluster": cluster_slug, "symbols": c.symbols}


# ------------------------------------------------------------------ merchants & deals

@mcp.tool()
async def merchants_needing_sources(limit: int = 5) -> list[dict]:
    """Merchants (new ones come from users' spending) whose website and social accounts are unknown."""
    async with system_session() as s:
        rows = (await s.execute(select(Merchant).where(Merchant.sources_status.in_(["pending", "failed"]))
                                .order_by(Merchant.seen_in_transactions.desc()).limit(limit))).scalars().all()
        for m in rows:
            m.sources_status = "discovering"
        return out([{"merchant_id": m.id, "name": m.name, "category": m.category_slug,
                     "subcategory": m.subcategory} for m in rows])


@mcp.tool()
async def save_merchant_sources(
    bot_name: str,
    merchant_id: str,
    found: bool,
    website: str | None = None,
    deals_page: str | None = None,
    instagram: str | None = None,
    facebook: str | None = None,
    tiktok: str | None = None,
    x: str | None = None,
    subcategory: str | None = None,
    cities: list[str] | None = None,
) -> dict:
    """Save the official website / deals page / social media accounts of a Pakistani merchant."""
    async with system_session() as s:
        m = await s.get(Merchant, uuid.UUID(merchant_id))
        if not m:
            return {"error": "unknown merchant"}
        m.website = website or m.website
        m.sources = {k: v for k, v in {**(m.sources or {}), "deals_page": deals_page, "instagram": instagram,
                                       "facebook": facebook, "tiktok": tiktok, "x": x}.items() if v}
        if subcategory:
            m.subcategory = subcategory[:80]
        if cities:
            m.cities = cities
        m.sources_status = "ready" if found and (m.website or m.sources) else "failed"
    await _mark_run(bot_name)
    return {"ok": True}


@mcp.tool()
async def merchants_to_crawl(limit: int = 5) -> list[dict]:
    """Merchants with known sources, least recently crawled first. Marks them as crawled now."""
    async with system_session() as s:
        rows = (await s.execute(select(Merchant).where(Merchant.sources_status == "ready")
                                .order_by(Merchant.last_crawled_at.nulls_first(),
                                          Merchant.seen_in_transactions.desc()).limit(limit))).scalars().all()
        for m in rows:
            m.last_crawled_at = datetime.now(UTC)
        return out([{"merchant_id": m.id, "name": m.name, "category": m.category_slug, "website": m.website,
                     "sources": m.sources} for m in rows])


@mcp.tool()
async def list_bank_names() -> list[str]:
    """Bank names to use in upsert_deal.bank."""
    async with system_session() as s:
        return [b for (b,) in (await s.execute(select(Bank.name).order_by(Bank.name))).all()]


@mcp.tool()
async def upsert_deal(
    bot_name: str,
    merchant: str,
    title: str,
    category: Literal["food", "grocery", "fuel", "medicine", "transport", "utilities", "shopping",
                      "entertainment", "education", "travel", "housing", "telecom", "misc"],
    source_url: str,
    source_kind: Literal["bank_site", "merchant_site", "instagram", "facebook", "tiktok", "aggregator", "other"],
    discount_type: Literal["percent", "flat", "bogo", "cashback", "other"] = "percent",
    discount_value: float | None = None,
    description: str = "",
    deal_type: str | None = None,
    max_discount: float | None = None,
    min_spend: float | None = None,
    requires_card: bool = False,
    bank: str | None = None,
    card_network: Literal["visa", "mastercard", "unionpay", "paypak", "amex"] | None = None,
    card_tier: str | None = None,
    card_type: Literal["debit", "credit"] | None = None,
    days_of_week: list[int] | None = None,
    cities: list[str] | None = None,
    valid_from: str | None = None,
    valid_until: str | None = None,
    confidence: float = 0.7,
) -> dict:
    """Insert or update a deal. deal_type is the specific kind, e.g. 'fast food restaurant', "women's apparel",
    "men's footwear". requires_card + bank/card_network/card_tier/card_type when the deal needs a specific card,
    otherwise it is generic. days_of_week uses 0=Mon..6=Sun ([] = every day). Dates are YYYY-MM-DD.
    Low confidence (<0.5) deals go to admin review instead of users."""
    vu = date.fromisoformat(valid_until) if valid_until else None
    vf = date.fromisoformat(valid_from) if valid_from else None
    if vu and vu < date.today():
        return {"ok": False, "error": "deal already expired"}
    async with system_session() as s:
        bank_id = None
        if bank:
            b = await s.scalar(select(Bank).where(or_(Bank.name.ilike(bank), Bank.short_name.ilike(bank))))
            bank_id = b.id if b else None
        merchant_row = await s.scalar(select(Merchant).where(Merchant.normalized_name == normalize_name(merchant)))
        values = dict(
            merchant_id=merchant_row.id if merchant_row else None, merchant_name=merchant[:160], title=title[:300],
            description=description[:4000], discount_type=discount_type, discount_value=discount_value,
            max_discount=max_discount, min_spend=min_spend, category_slug=category, deal_type=deal_type,
            requires_card=requires_card or bool(bank_id or card_network), bank_id=bank_id, card_network=card_network,
            card_tier=card_tier.lower() if card_tier else None, card_type=card_type, days_of_week=days_of_week or [],
            cities=cities or [], valid_from=vf, valid_until=vu, source_url=source_url[:500], source_kind=source_kind,
            status="active" if confidence >= 0.5 else "pending_review", confidence=max(0, min(1, confidence)),
        )
        fp = deal_fingerprint(merchant, title, bank, vu)
        res = await s.execute(
            insert(Deal).values(fingerprint=fp, **values)
            .on_conflict_do_update(index_elements=["fingerprint"],
                                   set_={k: v for k, v in values.items() if k != "status"} | {"updated_at": datetime.now(UTC)})
            .returning(Deal.id)
        )
        deal_id = res.scalar_one()
    await _mark_run(bot_name)
    return {"ok": True, "deal_id": str(deal_id)}


@mcp.tool()
async def list_deals(merchant: str | None = None, category: str | None = None, include_expired: bool = False,
                     limit: int = 50) -> list[dict]:
    """Deals currently in the database (for de-duplication and curation)."""
    async with system_session() as s:
        stmt = select(Deal)
        if not include_expired:
            stmt = stmt.where(Deal.status.in_(["active", "pending_review"]))
        if merchant:
            stmt = stmt.where(Deal.merchant_name.ilike(f"%{merchant}%"))
        if category:
            stmt = stmt.where(Deal.category_slug == category)
        rows = (await s.execute(stmt.order_by(Deal.updated_at.desc()).limit(min(limit, 200)))).scalars()
        return out([{"deal_id": d.id, "merchant": d.merchant_name, "title": d.title, "status": d.status,
                     "valid_until": d.valid_until, "source_url": d.source_url, "requires_card": d.requires_card,
                     "updated_at": d.updated_at} for d in rows])


@mcp.tool()
async def set_deal_status(bot_name: str, deal_id: str,
                          status: Literal["active", "expired", "pending_review", "rejected"]) -> dict:
    """Curator: expire, reject or re-activate a deal."""
    async with system_session() as s:
        d = await s.get(Deal, uuid.UUID(deal_id))
        if not d:
            return {"error": "unknown deal"}
        d.status = status
    await _mark_run(bot_name)
    return {"ok": True}


@mcp.tool()
async def expire_past_deals() -> dict:
    """Mark every deal whose valid_until is in the past as expired."""
    async with system_session() as s:
        res = await s.execute(update(Deal).where(Deal.valid_until < date.today(), Deal.status == "active")
                              .values(status="expired"))
        return {"expired": res.rowcount}


def build_app():
    return mcp.streamable_http_app()
