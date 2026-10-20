"""Optional profile photo, shown beside the person's own chat messages.

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("avatar", sa.LargeBinary(), nullable=True))
    op.add_column("user_profiles", sa.Column("avatar_type", sa.String(length=20), nullable=True))
    op.add_column("user_profiles", sa.Column("avatar_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "avatar_updated_at")
    op.drop_column("user_profiles", "avatar_type")
    op.drop_column("user_profiles", "avatar")
