"""Admins are not users: drop the profile, subscription and assistant chat that admin accounts used to get.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADMINS = "(SELECT id FROM users WHERE role = 'admin')"


def upgrade() -> None:
    op.execute("SELECT set_config('app.role', 'system', true)")  # tables use FORCE ROW LEVEL SECURITY
    # The gateway removes the OpenMausBot teams of these rooms on its next sync (admins are not "known users").
    for table in ("chat_messages", "chat_rooms", "notifications", "user_facts", "subscriptions", "user_profiles"):
        op.execute(f"DELETE FROM {table} WHERE user_id IN {ADMINS}")


def downgrade() -> None:
    pass  # the removed rows were never meant to exist
