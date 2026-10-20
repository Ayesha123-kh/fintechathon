"""Notifications live in the chat: track when the chat was last read and copy old notifications into it.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("chat_read_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("SELECT set_config('app.role', 'system', true)")  # tables use FORCE ROW LEVEL SECURITY
    # Every past notification (except announcements of bot replies, which are already chat messages)
    # becomes a chat message from "Paisave".
    op.execute("""
        INSERT INTO chat_messages (id, user_id, omb_message_id, role, sender, text, kind, final, created_at, updated_at)
        SELECT gen_random_uuid(), n.user_id, NULL, 'bot', 'Paisave', '**' || n.title || E'**\\n' || n.body,
               'notification', true, n.created_at, n.created_at
        FROM notifications n WHERE n.kind <> 'chat'
    """)
    # Unread = anything after the oldest unread notification; everything else counts as read.
    op.execute("""
        UPDATE user_profiles p SET chat_read_at = COALESCE(
            (SELECT min(n.created_at) - interval '1 second' FROM notifications n
             WHERE n.user_id = p.user_id AND n.read_at IS NULL),
            now())
    """)


def downgrade() -> None:
    op.execute("SELECT set_config('app.role', 'system', true)")
    op.execute("DELETE FROM chat_messages WHERE kind = 'notification'")
    op.drop_column("user_profiles", "chat_read_at")
