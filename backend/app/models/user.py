import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UserOwned, UUIDPk


class User(UUIDPk, Timestamps, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200), default="")
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserProfile(Timestamps, Base):
    """Financial profile the chatbot fills in during onboarding and keeps up to date."""

    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    monthly_income: Mapped[Decimal | None]
    salary_day: Mapped[int | None] = mapped_column(Integer)  # day of month salary usually arrives
    currency: Mapped[str] = mapped_column(String(3), default="PKR")
    city: Mapped[str | None] = mapped_column(String(80))
    language: Mapped[str] = mapped_column(String(20), default="en")  # en | ur | roman_ur
    # How savings are separated from the expendable amount each month.
    savings_mode: Mapped[str] = mapped_column(String(20), default="percent")  # percent | fixed | leftover
    savings_value: Mapped[Decimal | None]
    # How the monthly savings are divided between active goals.
    goal_split_mode: Mapped[str] = mapped_column(String(20), default="deadline")  # equal|priority|custom|deadline
    sadqah_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    sadqah_mode: Mapped[str | None] = mapped_column(String(20))  # percent_income | fixed
    sadqah_value: Mapped[Decimal | None]
    sadqah_frequency: Mapped[str | None] = mapped_column(String(20))  # weekly | friday | monthly
    investment_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    investment_disclaimer_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    risk_profile: Mapped[str | None] = mapped_column(String(20))  # conservative | moderate | aggressive
    preferred_places: Mapped[list] = mapped_column(JSONB, default=list)
    notification_prefs: Mapped[dict] = mapped_column(JSONB, default=dict)
    onboarding_state: Mapped[dict] = mapped_column(JSONB, default=dict)
    # When the person last opened the chat; later bot messages and notifications count as unread.
    chat_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserFact(UUIDPk, UserOwned, Base):
    """Long-lived facts the assistant learned (e.g. 'got a 15% increment in Oct 2026')."""

    __tablename__ = "user_facts"

    fact: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(40), default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WebAuthnCredential(UUIDPk, UserOwned, Base):
    __tablename__ = "webauthn_credentials"

    credential_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports: Mapped[list] = mapped_column(JSONB, default=list)
    device_name: Mapped[str] = mapped_column(String(120), default="This device")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PushSubscription(UUIDPk, UserOwned, Base):
    __tablename__ = "push_subscriptions"

    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))
    user_agent: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(UUIDPk, UserOwned, Base):
    __tablename__ = "notifications"

    kind: Mapped[str] = mapped_column(String(40))  # chat | motivation | sadqah | deal | goal | system
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(300), default="/dashboard")
    pushed: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EmailConnection(UUIDPk, UserOwned, Timestamps, Base):
    __tablename__ = "email_connections"

    provider: Mapped[str] = mapped_column(String(20), default="gmail")
    email_address: Mapped[str] = mapped_column(String(320))
    access_token_enc: Mapped[str] = mapped_column(Text)
    refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | error | revoked
    last_error: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_from: Mapped[date | None] = mapped_column(Date)


class IngestedEmail(UUIDPk, UserOwned, Base):
    """Every Gmail message we looked at, so it is processed exactly once."""

    __tablename__ = "ingested_emails"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_connections.id", ondelete="CASCADE")
    )
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(20))  # transaction | ignored | error
    subject: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
