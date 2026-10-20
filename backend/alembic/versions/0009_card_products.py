"""Catalog of the card products the supported banks issue (global reference data, filled at startup).

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.core.config import settings

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAFF = "current_setting('app.role', true) IN ('admin', 'system')"


def upgrade() -> None:
    op.create_table(
        "card_products",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("bank_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("network", sa.String(length=20), nullable=True),
        sa.Column("tier", sa.String(length=30), nullable=True),
        sa.Column("card_type", sa.String(length=10), nullable=False),
        sa.Column("is_islamic", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confidence", sa.String(length=12), nullable=False, server_default="bank_site"),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("verified_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bank_id"], ["banks.id"], name=op.f("fk_card_products_bank_id_banks"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_card_products")),
        sa.UniqueConstraint("bank_id", "name", name="uq_card_products_bank_name"),
    )
    op.create_index(op.f("ix_card_products_bank_id"), "card_products", ["bank_id"], unique=False)

    # Like the other shared tables: everyone reads, only admin/system write. (Not in GLOBAL_TABLES on purpose:
    # migration 0001 iterates that list and this table does not exist yet at that point.)
    role = settings.app_db_role
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON card_products TO {role}")
    op.execute("ALTER TABLE card_products ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE card_products FORCE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY card_products_read ON card_products FOR SELECT USING (true)")
    op.execute(f"CREATE POLICY card_products_write ON card_products FOR ALL USING ({STAFF}) WITH CHECK ({STAFF})")


def downgrade() -> None:
    op.drop_index(op.f("ix_card_products_bank_id"), table_name="card_products")
    op.drop_table("card_products")
