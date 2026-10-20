"""Merchants from users' spending are screened by the self-hosted model before the deal bots can see them.

Merchants that came from transactions and were not yet handed to the Source Scout go back to 'screening';
the worker judges them (business -> 'pending', private payee -> 'personal') once the model is reachable.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("SELECT set_config('app.role', 'system', true)")  # tables use FORCE ROW LEVEL SECURITY
    op.execute("UPDATE merchants SET sources_status = 'screening' "
               "WHERE seen_in_transactions > 0 AND sources_status IN ('pending', 'failed')")


def downgrade() -> None:
    op.execute("SELECT set_config('app.role', 'system', true)")
    op.execute("UPDATE merchants SET sources_status = 'pending' WHERE sources_status = 'screening'")
