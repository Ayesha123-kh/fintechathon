"""Remember which deals the assistant told each person about, so using one can be detected from their spending.

Also makes a redemption unique per transaction, so a bank alert can never be counted twice.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_CHECK = (
    "user_id::text = current_setting('app.user_id', true) "
    "OR current_setting('app.role', true) IN ('admin', 'system')"
)


def upgrade() -> None:
    op.create_table(
        "deal_offers",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="open"),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_deal_offers_user_id_users"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], name=op.f("fk_deal_offers_deal_id_deals"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deal_offers")),
    )
    op.create_index(op.f("ix_deal_offers_user_id"), "deal_offers", ["user_id"], unique=False)
    op.create_index(op.f("ix_deal_offers_deal_id"), "deal_offers", ["deal_id"], unique=False)
    # One open offer per person and deal; a redeemed one can be offered again later.
    op.create_index("uq_deal_offers_open", "deal_offers", ["user_id", "deal_id"], unique=True,
                    postgresql_where=sa.text("status = 'open'"))
    op.create_index("uq_deal_redemptions_transaction", "deal_redemptions", ["transaction_id"], unique=True,
                    postgresql_where=sa.text("transaction_id IS NOT NULL"))

    # Same isolation as the other user-owned tables. (Not in USER_OWNED_TABLES: migration 0001 iterates that
    # list and this table does not exist yet at that point.)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON deal_offers TO {settings.app_db_role}")
    op.execute("ALTER TABLE deal_offers ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE deal_offers FORCE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY deal_offers_isolation ON deal_offers USING ({USER_CHECK}) WITH CHECK ({USER_CHECK})")


def downgrade() -> None:
    op.drop_index("uq_deal_redemptions_transaction", table_name="deal_redemptions")
    op.drop_table("deal_offers")
