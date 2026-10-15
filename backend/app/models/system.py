import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UserOwned, UUIDPk


class ChatRoom(Timestamps, Base):
    """Link between a user and their private OpenMausBot group chat."""

    __tablename__ = "chat_rooms"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    omb_room_id: Mapped[str | None] = mapped_column(String(80), index=True)
    omb_thread_id: Mapped[str | None] = mapped_column(String(80), index=True)
    # Lookup by hash, keep an encrypted copy to rewrite the room bulletin.
    member_key_hash: Mapped[str] = mapped_column(String(64), unique=True)
    member_key_enc: Mapped[str] = mapped_column(Text)
    bots: Mapped[dict] = mapped_column(JSONB, default=dict)  # {role: {id, name}}
    soul_version: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | ready | error
    last_error: Mapped[str | None] = mapped_column(Text)


class ChatMessage(UUIDPk, UserOwned, Base):
    __tablename__ = "chat_messages"

    omb_message_id: Mapped[str | None] = mapped_column(String(80), unique=True)
    role: Mapped[str] = mapped_column(String(10))  # user | bot | system
    sender: Mapped[str] = mapped_column(String(80), default="")
    text: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(20), default="text")
    final: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AgentRegistry(Timestamps, Base):
    """What the gateway created in OpenMausBot (for the admin dashboard)."""

    __tablename__ = "agent_registry"

    name: Mapped[str] = mapped_column(String(120), primary_key=True)
    team: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(20))  # shared | user_template | watcher
    soul_hash: Mapped[str | None] = mapped_column(String(64))
    omb_bot_id: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="ok")
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class Plan(UUIDPk, Timestamps, Base):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    price_monthly: Mapped[Decimal] = mapped_column(default=0)
    currency: Mapped[str] = mapped_column(String(3), default="PKR")
    features: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subscription(UUIDPk, UserOwned, Timestamps, Base):
    """Ready for a payment gateway: provider ids are filled in when one is integrated."""

    __tablename__ = "subscriptions"

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")  # trialing|active|past_due|canceled
    provider: Mapped[str | None] = mapped_column(String(30))
    provider_customer_id: Mapped[str | None] = mapped_column(String(120))
    provider_subscription_id: Mapped[str | None] = mapped_column(String(120))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)


class Payment(UUIDPk, UserOwned, Base):
    __tablename__ = "payments"

    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    amount: Mapped[Decimal]
    currency: Mapped[str] = mapped_column(String(3), default="PKR")
    provider: Mapped[str | None] = mapped_column(String(30))
    provider_ref: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|succeeded|failed|refunded
    raw: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(UUIDPk, Base):
    __tablename__ = "audit_log"

    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(80))
    target: Mapped[str] = mapped_column(String(200), default="")
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
