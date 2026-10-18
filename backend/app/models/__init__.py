from app.models.base import Base
from app.models.finance import (
    Bank,
    BankAccount,
    Card,
    CardProduct,
    Category,
    DealOffer,
    DealRedemption,
    Goal,
    SavingsEntry,
    Transaction,
)
from app.models.market import (
    AssetClass,
    CoverageRequest,
    Deal,
    MarketSignal,
    Merchant,
    ResearchNote,
    UserFollow,
    WatchCluster,
)
from app.models.system import AgentRegistry, AuditLog, ChatMessage, ChatRoom, Payment, Plan, Subscription
from app.models.user import (
    EmailConnection,
    IngestedEmail,
    Notification,
    PushSubscription,
    User,
    UserFact,
    UserProfile,
    WebAuthnCredential,
)

# Tables whose rows belong to one user: RLS on user_id (users itself uses id).
USER_OWNED_TABLES = [
    "user_profiles",
    "user_facts",
    "webauthn_credentials",
    "push_subscriptions",
    "notifications",
    "email_connections",
    "ingested_emails",
    "bank_accounts",
    "cards",
    "goals",
    "savings_ledger",
    "transactions",
    "deal_redemptions",
    "user_follows",
    "coverage_requests",
    "chat_rooms",
    "chat_messages",
    "subscriptions",
    "payments",
]

# Shared tables: everyone may read, only admin/system may write.
GLOBAL_TABLES = [
    "banks",
    "categories",
    "merchants",
    "deals",
    "asset_classes",
    "watch_clusters",
    "market_signals",
    "research_notes",
    "plans",
]

# Admin/system only.
PRIVATE_TABLES = ["agent_registry", "audit_log"]

__all__ = [
    "GLOBAL_TABLES",
    "PRIVATE_TABLES",
    "USER_OWNED_TABLES",
    "AgentRegistry",
    "AssetClass",
    "AuditLog",
    "Bank",
    "BankAccount",
    "Base",
    "Card",
    "CardProduct",
    "Category",
    "ChatMessage",
    "ChatRoom",
    "CoverageRequest",
    "Deal",
    "DealOffer",
    "DealRedemption",
    "EmailConnection",
    "Goal",
    "IngestedEmail",
    "MarketSignal",
    "Merchant",
    "Notification",
    "Payment",
    "Plan",
    "PushSubscription",
    "ResearchNote",
    "SavingsEntry",
    "Subscription",
    "Transaction",
    "User",
    "UserFact",
    "UserFollow",
    "UserProfile",
    "WatchCluster",
    "WebAuthnCredential",
]
