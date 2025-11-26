"""Alembic environment configuration."""
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import asyncio
import sys
import re

# Import all models to ensure they're registered with Base
from app.core.database import Base
from app.models import *  # noqa
from app.core.config import settings

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url with our DATABASE_URL
database_url = settings.database_url
config.set_main_option("sqlalchemy.url", database_url)

# Debug logging
print("\n" + "="*70, file=sys.stderr)
print("ALEMBIC DEBUG INFO", file=sys.stderr)
print("="*70, file=sys.stderr)
print(f"Settings DATABASE_URL: {database_url}", file=sys.stderr)

# Parse and show details (hide password)
# Parse and show details (hide password)
if match := re.match(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url):
    user, password, host, port, db = match.groups()
    print(f"  Parsed User: {user}", file=sys.stderr)
    print(f"  Parsed Password length: {len(password)} chars", file=sys.stderr)
    print(f"  Parsed Host: {host}", file=sys.stderr)
    print(f"  Parsed Port: {port}", file=sys.stderr)
    print(f"  Parsed Database: {db}", file=sys.stderr)
elif database_url.startswith("sqlite"):
    print(f"  Using SQLite Database: {database_url}", file=sys.stderr)
print("="*70 + "\n", file=sys.stderr)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        render_as_batch=True
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    # Get the config section and ensure sqlalchemy.url is set correctly
    configuration = config.get_section(config.config_ini_section, {})
    # Override with our DATABASE_URL (the set_main_option above doesn't update the section dict)
    configuration["sqlalchemy.url"] = database_url
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
