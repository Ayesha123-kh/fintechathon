"""Global (non user-specific) data maintained by the shared agent teams."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UserOwned, UUIDPk


class Merchant(UUIDPk, Timestamps, Base):
    __tablename__ = "merchants"

    name: Mapped[str] = mapped_column(String(160))
    normalized_name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    category_slug: Mapped[str] = mapped_column(String(40), ForeignKey("categories.slug"), default="misc")
    subcategory: Mapped[str | None] = mapped_column(String(80))  # e.g. "fast food restaurant"
    cities: Mapped[list] = mapped_column(JSONB, default=list)
    website: Mapped[str | None] = mapped_column(String(300))
    # {"instagram": url, "facebook": url, "tiktok": url, "x": url, "deals_page": url}
    sources: Mapped[dict] = mapped_column(JSONB, default=dict)
    # pending -> discovering -> ready | failed
    sources_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    seen_in_transactions: Mapped[int] = mapped_column(Integer, default=0)
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Deal(UUIDPk, Timestamps, Base):
    __tablename__ = "deals"

    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="SET NULL"), index=True
    )
    merchant_name: Mapped[str] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text, default="")
    discount_type: Mapped[str] = mapped_column(String(20), default="percent")  # percent|flat|bogo|cashback|other
    discount_value: Mapped[Decimal | None]
    max_discount: Mapped[Decimal | None]
    min_spend: Mapped[Decimal | None]
    category_slug: Mapped[str] = mapped_column(String(40), ForeignKey("categories.slug"), default="misc")
    deal_type: Mapped[str | None] = mapped_column(String(80))  # "fast food restaurant", "women's apparel" ...
    requires_card: Mapped[bool] = mapped_column(Boolean, default=False)
    bank_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("banks.id"))
    card_network: Mapped[str | None] = mapped_column(String(20))
    card_tier: Mapped[str | None] = mapped_column(String(30))
    card_type: Mapped[str | None] = mapped_column(String(10))
    days_of_week: Mapped[list] = mapped_column(JSONB, default=list)  # [] = every day; 0=Mon
    cities: Mapped[list] = mapped_column(JSONB, default=list)  # [] = nationwide
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date, index=True)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_kind: Mapped[str] = mapped_column(String(20), default="other")
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|expired|pending_review|rejected
    verified_by_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)


class AssetClass(Base):
    __tablename__ = "asset_classes"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")


class WatchCluster(UUIDPk, Timestamps, Base):
    """A group of related assets watched by one watcher bot (e.g. PSX oil & gas)."""

    __tablename__ = "watch_clusters"

    asset_class: Mapped[str] = mapped_column(String(40), ForeignKey("asset_classes.slug"))
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    symbols: Mapped[list] = mapped_column(JSONB, default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MarketSignal(UUIDPk, Base):
    __tablename__ = "market_signals"

    asset_class: Mapped[str] = mapped_column(String(40), ForeignKey("asset_classes.slug"), index=True)
    cluster_slug: Mapped[str | None] = mapped_column(String(60))
    symbol: Mapped[str] = mapped_column(String(40), index=True)
    signal: Mapped[str] = mapped_column(String(10))  # buy | sell | hold | watch | alert
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    horizon: Mapped[str | None] = mapped_column(String(20))  # intraday | swing | long_term
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ResearchNote(UUIDPk, Base):
    __tablename__ = "research_notes"

    asset_class: Mapped[str] = mapped_column(String(40), ForeignKey("asset_classes.slug"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="research")  # research | analysis
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, default="")
    sentiment: Mapped[str | None] = mapped_column(String(10))  # bullish | bearish | neutral
    symbols: Mapped[list] = mapped_column(JSONB, default=list)
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    created_by: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class UserFollow(UUIDPk, UserOwned, Base):
    __tablename__ = "user_follows"

    asset_class: Mapped[str] = mapped_column(String(40), ForeignKey("asset_classes.slug"))
    symbol: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CoverageRequest(UUIDPk, UserOwned, Base):
    """A user asked about an asset no watcher covers yet."""

    __tablename__ = "coverage_requests"

    asset_class: Mapped[str] = mapped_column(String(40), ForeignKey("asset_classes.slug"))
    symbol: Mapped[str] = mapped_column(String(40))
    note: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | added | rejected
    resolved_cluster: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
