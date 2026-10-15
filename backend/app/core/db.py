"""Database engine and RLS-aware sessions.

Every session runs inside one transaction whose `app.user_id` / `app.role` settings
are set with `set_config(..., true)` (transaction local). Postgres row level security
policies (see the initial migration) read those settings, so a query can never see
another user's rows even if application code forgets a WHERE clause.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def _apply_context(session: AsyncSession, user_id: UUID | None, role: str) -> None:
    await session.execute(
        text("SELECT set_config('app.user_id', :uid, true), set_config('app.role', :role, true)"),
        {"uid": str(user_id) if user_id else "", "role": role},
    )


@asynccontextmanager
async def scoped_session(user_id: UUID | None = None, role: str = "user") -> AsyncIterator[AsyncSession]:
    """A transaction scoped to one user (role 'user'), an admin ('admin') or background jobs ('system')."""
    async with SessionFactory() as session, session.begin():
        await _apply_context(session, user_id, role)
        yield session


@asynccontextmanager
async def system_session() -> AsyncIterator[AsyncSession]:
    async with scoped_session(None, "system") as session:
        yield session
