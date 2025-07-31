"""
Alembic environment configuration for Infrastructure Management MCP Server.

This configuration supports both async SQLAlchemy and TimescaleDB-specific
migrations including hypertables, continuous aggregates, and policies.
"""

import os
import sys
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Import standalone models file for Alembic
import importlib.util
models_path = os.path.join(os.path.dirname(__file__), 'models.py')
spec = importlib.util.spec_from_file_location("alembic_models", models_path)
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)
Base = models.Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Simple database URL configuration for Alembic
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "9100")
POSTGRES_DB = os.getenv("POSTGRES_DB", "infrastructor")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "change_me_in_production")

# Set the database URL from environment configuration
SYNC_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
ASYNC_DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

config.set_main_option("sqlalchemy.url", SYNC_DATABASE_URL)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_name(name, type_, parent_names):
    """
    Filter function to control which database objects are included in autogenerate.
    
    This function excludes TimescaleDB internal objects and focuses on our application tables.
    """
    if type_ == "table":
        # Exclude TimescaleDB internal tables
        timescaledb_tables = [
            "_timescaledb_internal",
            "_timescaledb_catalog",
            "_timescaledb_config",
            "_timescaledb_cache",
            "timescaledb_information",
            "timescaledb_experimental"
        ]
        
        for ts_table in timescaledb_tables:
            if name.startswith(ts_table):
                return False
        
        # Include our application tables
        app_tables = [
            "devices", "system_metrics", "drive_health", "container_snapshots",
            "zfs_status", "zfs_snapshots", "network_interfaces", "docker_networks",
            "vm_status", "system_logs", "backup_status", "system_updates"
        ]
        
        return name in app_tables
    
    return True


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter function for more detailed object inclusion control.
    
    This ensures we only manage our application objects in migrations.
    """
    if type_ == "table" and reflected and compare_to is not None:
        # Skip TimescaleDB system tables
        if name.startswith(("_timescaledb", "timescaledb_")):
            return False
    
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_name=include_name,
        include_object=include_object,
        # TimescaleDB-specific options
        render_as_batch=False,  # Don't use batch operations
        transaction_per_migration=True,  # Use transactions for each migration
        compare_type=True,  # Compare column types
        compare_server_default=True,  # Compare server defaults
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_name=include_name,
        include_object=include_object,
        # TimescaleDB-specific options
        render_as_batch=False,  # Don't use batch operations
        transaction_per_migration=True,  # Use transactions for each migration
        compare_type=True,  # Compare column types
        compare_server_default=True,  # Compare server defaults
        # Version table options
        version_table_schema=None,  # Use default schema
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = ASYNC_DATABASE_URL
    
    # Create async engine
    connectable = create_async_engine(
        ASYNC_DATABASE_URL,
        poolclass=pool.NullPool,
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Check if we're in an async context
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we're already in an async context, run the async version
        asyncio.create_task(run_async_migrations())
    except RuntimeError:
        # No event loop running, we can run async migrations directly
        asyncio.run(run_async_migrations())


# Migration execution
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()