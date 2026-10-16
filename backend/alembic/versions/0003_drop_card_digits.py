"""Stop storing card digits: only the card type (e.g. "Visa Silver Debit Card of Meezan Bank") is kept.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("cards", "last4")


def downgrade() -> None:
    op.add_column("cards", sa.Column("last4", sa.String(length=4), nullable=True))
