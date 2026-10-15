import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamps, UserOwned, UUIDPk


class Bank(UUIDPk, Base):
    """Directory of Pakistani banks and wallets (global)."""

    __tablename__ = "banks"

    name: Mapped[str] = mapped_column(String(120), unique=True)
    short_name: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(20), default="bank")  # bank | islamic_bank | wallet
    website: Mapped[str | None] = mapped_column(String(200))
    # Sender domains used by transaction alert emails.
    email_domains: Mapped[list] = mapped_column(JSONB, default=list)
    aliases: Mapped[list] = mapped_column(JSONB, default=list)


class Category(Base):
    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    icon: Mapped[str] = mapped_column(String(40), default="circle")
    color: Mapped[str] = mapped_column(String(9), default="#B0E454")
    is_expense: Mapped[bool] = mapped_column(Boolean, default=True)


class BankAccount(UUIDPk, UserOwned, Timestamps, Base):
    __tablename__ = "bank_accounts"

    bank_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("banks.id"))
    nickname: Mapped[str] = mapped_column(String(80), default="")
    account_type: Mapped[str] = mapped_column(String(20), default="current")  # current | savings | wallet
    last4: Mapped[str | None] = mapped_column(String(4))
    balance: Mapped[Decimal] = mapped_column(default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


class Card(UUIDPk, UserOwned, Timestamps, Base):
    __tablename__ = "cards"

    bank_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("banks.id"))
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="SET NULL")
    )
    network: Mapped[str] = mapped_column(String(20))  # visa | mastercard | unionpay | paypak | amex
    tier: Mapped[str | None] = mapped_column(String(30))  # classic | silver | gold | platinum | titanium ...
    card_type: Mapped[str] = mapped_column(String(10), default="debit")  # debit | credit
    label: Mapped[str] = mapped_column(String(120))  # e.g. "Visa Silver Card of Meezan Bank"
    last4: Mapped[str | None] = mapped_column(String(4))


class Goal(UUIDPk, UserOwned, Timestamps, Base):
    __tablename__ = "goals"

    name: Mapped[str] = mapped_column(String(120))
    target_amount: Mapped[Decimal]
    saved_amount: Mapped[Decimal] = mapped_column(default=0)
    deadline: Mapped[date | None] = mapped_column(Date)
    priority: Mapped[int] = mapped_column(Integer, default=3)  # 1 (highest) .. 5
    weight: Mapped[Decimal | None]  # custom split percentage
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|paused|completed|cancelled
    icon: Mapped[str] = mapped_column(String(40), default="target")
    notes: Mapped[str] = mapped_column(Text, default="")


class SavingsEntry(UUIDPk, UserOwned, Base):
    """Ledger of money earmarked as savings. Goal.saved_amount is the sum per goal."""

    __tablename__ = "savings_ledger"

    goal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"))
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="SET NULL")
    )
    amount: Mapped[Decimal]
    # allocation | deal_saving | manual | withdrawal | sadqah | goal_completed
    source: Mapped[str] = mapped_column(String(20))
    note: Mapped[str] = mapped_column(Text, default="")
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Transaction(UUIDPk, UserOwned, Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("user_id", "external_id", name="uq_transactions_user_external"),)

    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="SET NULL")
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    amount: Mapped[Decimal]
    direction: Mapped[str] = mapped_column(String(6))  # debit | credit
    merchant_raw: Mapped[str] = mapped_column(String(200), default="")
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="SET NULL")
    )
    category_slug: Mapped[str] = mapped_column(String(40), ForeignKey("categories.slug"), default="misc")
    description: Mapped[str] = mapped_column(Text, default="")
    channel: Mapped[str] = mapped_column(String(20), default="other")  # card|transfer|atm|online|bill|other
    source: Mapped[str] = mapped_column(String(20), default="manual")  # gmail | manual | chat
    external_id: Mapped[str | None] = mapped_column(String(128))
    balance_after: Mapped[Decimal | None]
    is_income: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DealRedemption(UUIDPk, UserOwned, Base):
    __tablename__ = "deal_redemptions"

    deal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("deals.id", ondelete="SET NULL"))
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL")
    )
    amount_spent: Mapped[Decimal]
    amount_saved: Mapped[Decimal]
    goal_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
