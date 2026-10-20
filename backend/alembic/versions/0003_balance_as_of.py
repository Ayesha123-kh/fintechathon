"""Remember when each account balance was last known, so imported bank alerts older than that don't change it again.

Existing accounts count their balance as known from when they were added.

Revision ID: 0004
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bank_accounts", sa.Column("balance_as_of", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE bank_accounts SET balance_as_of = created_at")


def downgrade() -> None:
    op.drop_column("bank_accounts", "balance_as_of")
