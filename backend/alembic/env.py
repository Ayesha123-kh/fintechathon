import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import settings
from app.models import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=settings.migration_database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    # Migrations run as the schema owner, never as the RLS-restricted app role.
    engine = create_async_engine(settings.migration_database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
