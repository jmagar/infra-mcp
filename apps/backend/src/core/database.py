"""
Infrastructure Management MCP Server - Database Configuration

This module provides async SQLAlchemy setup with TimescaleDB-optimized
connection pooling, session management, and dependency injection.
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
import asyncio
import logging
from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy.orm import sessionmaker

from .config import get_settings

# Configure logging
logger = logging.getLogger(__name__)

# Global database engine and session factory
_async_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None

# TimescaleDB-specific metadata naming convention for constraints and indexes
custom_metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

# SQLAlchemy declarative base with custom metadata
Base = declarative_base(metadata=custom_metadata)


def create_async_database_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine with TimescaleDB-optimized configuration.

    Returns:
        AsyncEngine: Configured async database engine
    """
    settings = get_settings()

    # Engine configuration optimized for TimescaleDB
    engine_config = {
        "url": settings.database.database_url,
        "echo": settings.debug,  # SQL logging in debug mode
        "echo_pool": settings.debug,  # Connection pool logging in debug mode
        "future": True,  # Use SQLAlchemy 2.0 style
        "poolclass": AsyncAdaptedQueuePool,
        "pool_size": settings.database.db_pool_size,
        "max_overflow": settings.database.db_max_overflow,
        "pool_timeout": settings.database.db_pool_timeout,
        "pool_recycle": settings.database.db_pool_recycle,
        "pool_pre_ping": True,  # Validate connections before use
        # TimescaleDB-specific optimizations
        "connect_args": {
            "command_timeout": 60,  # Command timeout for long-running queries
            "server_settings": {
                "application_name": "infrastructor_mcp",
                "jit": "off",  # Disable JIT for TimescaleDB compatibility
                "timezone": "UTC",  # Use UTC for all timestamp operations
                "statement_timeout": "60s",  # Global statement timeout
                "lock_timeout": "30s",  # Lock timeout for concurrent operations
            },
        },
    }

    # Use NullPool for testing/development if specified
    if settings.environment == "testing":
        engine_config["poolclass"] = NullPool
        logger.info("Using NullPool for testing environment")

    engine = create_async_engine(**engine_config)

    logger.info(
        f"Created async database engine: {settings.database.postgres_host}:"
        f"{settings.database.postgres_port}/{settings.database.postgres_db}"
    )

    return engine


def create_async_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Create async session factory for database operations.

    Args:
        engine: Async SQLAlchemy engine

    Returns:
        async_sessionmaker: Session factory for creating async sessions
    """
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Don't expire instances on commit
        autoflush=True,  # Auto-flush before queries
        autocommit=False,  # Manual transaction control
    )

    logger.info("Created async session factory")
    return session_factory


async def init_database() -> None:
    """
    Initialize database connection and global session factory.
    Should be called during application startup.
    """
    global _async_engine, _async_session_factory

    if _async_engine is not None:
        logger.warning("Database already initialized")
        return

    try:
        # Create async engine
        _async_engine = create_async_database_engine()

        # Create session factory
        _async_session_factory = create_async_session_factory(_async_engine)

        # Test connection
        await test_database_connection()

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database() -> None:
    """
    Close database connections and cleanup resources.
    Should be called during application shutdown.
    """
    global _async_engine, _async_session_factory

    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("Database connections closed")


def get_async_engine() -> AsyncEngine:
    """
    Get the global async database engine.

    Returns:
        AsyncEngine: Global database engine

    Raises:
        RuntimeError: If database is not initialized
    """
    if _async_engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _async_engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the global async session factory.

    Returns:
        async_sessionmaker: Global session factory

    Raises:
        RuntimeError: If database is not initialized
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _async_session_factory


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session with automatic cleanup.

    Usage:
        async with get_async_session() as session:
            result = await session.execute(query)
            await session.commit()

    Yields:
        AsyncSession: Database session
    """
    session_factory = get_async_session_factory()

    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection function for FastAPI to get database session.

    Yields:
        AsyncSession: Database session for FastAPI dependency injection
    """
    async with get_async_session() as session:
        yield session


async def test_database_connection() -> bool:
    """
    Test database connectivity and TimescaleDB extension.

    Returns:
        bool: True if connection successful

    Raises:
        Exception: If connection fails
    """
    try:
        async with get_async_session() as session:
            # Test basic connectivity
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

            # Test TimescaleDB extension
            result = await session.execute(
                text(
                    "SELECT installed_version FROM pg_available_extensions WHERE name = 'timescaledb'"
                )
            )
            timescale_version = result.scalar()

            if timescale_version:
                logger.info(f"TimescaleDB extension version: {timescale_version}")
            else:
                logger.warning("TimescaleDB extension not found")

            # Test UUID extension
            result = await session.execute(
                text(
                    "SELECT installed_version FROM pg_available_extensions WHERE name = 'uuid-ossp'"
                )
            )
            uuid_version = result.scalar()

            if uuid_version:
                logger.info(f"UUID-OSSP extension version: {uuid_version}")
            else:
                logger.warning("UUID-OSSP extension not found")

            logger.info("Database connection test successful")
            return True

    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        raise


async def check_database_health() -> dict:
    """
    Comprehensive database health check for monitoring.

    Returns:
        dict: Health check results with metrics
    """
    health_data = {
        "status": "unknown",
        "connection_pool": {},
        "database_info": {},
        "table_counts": {},
        "performance_metrics": {},
    }

    try:
        engine = get_async_engine()

        # Check connection pool status
        pool = engine.pool
        health_data["connection_pool"] = {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            # AsyncAdaptedQueuePool doesn't have invalid() method
            "pool_class": str(type(pool).__name__),
        }

        async with get_async_session() as session:
            # Basic connectivity
            await session.execute(text("SELECT 1"))

            # PostgreSQL version and extension info
            result = await session.execute(text("SELECT version()"))
            pg_version = result.scalar()

            result = await session.execute(
                text("SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'btree_gin', 'btree_gist')")
            )
            extensions = [row[0] for row in result.fetchall()]

            health_data["database_info"] = {
                "postgresql_version": pg_version,
                "extensions": extensions,
                "database_type": "PostgreSQL",
            }

            # Table counts for key tables
            tables_to_check = ["devices", "system_metrics", "drive_health", "container_snapshots"]
            for table in tables_to_check:
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    health_data["table_counts"][table] = result.scalar()
                except Exception as e:
                    health_data["table_counts"][table] = f"Error: {e}"

            # Performance metrics
            result = await session.execute(
                text(
                    "SELECT datname, numbackends, xact_commit, xact_rollback FROM pg_stat_database WHERE datname = current_database()"
                )
            )
            db_stats = result.fetchone()

            if db_stats:
                health_data["performance_metrics"] = {
                    "active_connections": db_stats[1],
                    "transactions_committed": db_stats[2],
                    "transactions_rolled_back": db_stats[3],
                }

            health_data["status"] = "healthy"

    except Exception as e:
        health_data["status"] = "unhealthy"
        health_data["error"] = str(e)
        logger.error(f"Database health check failed: {e}")

    return health_data


async def execute_raw_sql(query: str, params: dict = None) -> any:
    """
    Execute raw SQL query with parameters.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        Query result
    """
    async with get_async_session() as session:
        result = await session.execute(text(query), params or {})
        return result


async def get_database_stats() -> dict:
    """
    Get comprehensive database statistics for monitoring.

    Returns:
        dict: Database statistics including sizes and performance metrics
    """
    stats = {}

    try:
        async with get_async_session() as session:
            # Database size
            result = await session.execute(
                text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            )
            stats["database_size"] = result.scalar()

            # Table sizes for hypertables
            result = await session.execute(
                text("""
                    SELECT 
                        table_name,
                        pg_size_pretty(total_bytes) as total_size,
                        pg_size_pretty(table_bytes) as table_size,
                        pg_size_pretty(index_bytes) as index_size,
                        num_chunks
                    FROM hypertable_detailed_size 
                    ORDER BY total_bytes DESC
                """)
            )
            stats["hypertable_sizes"] = [dict(row) for row in result.fetchall()]

            # Recent activity
            result = await session.execute(
                text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes
                    FROM pg_stat_user_tables 
                    WHERE schemaname = 'public'
                    ORDER BY n_tup_ins DESC
                """)
            )
            stats["table_activity"] = [dict(row) for row in result.fetchall()]

    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        stats["error"] = str(e)

    return stats


async def create_hypertables() -> dict:
    """
    Create TimescaleDB hypertables for time-series tables.
    This function should be called after running Alembic migrations.

    Returns:
        dict: Results of hypertable creation operations
    """
    results = {"created": [], "skipped": [], "errors": []}

    # Define hypertables to create
    hypertables = [
        ("system_metrics", "time", "1 day"),
        ("drive_health", "time", "1 day"),
        ("container_snapshots", "time", "1 day"),
        ("zfs_status", "time", "1 day"),
        ("zfs_snapshots", "time", "1 day"),
        ("network_interfaces", "time", "1 day"),
        ("docker_networks", "time", "1 day"),
        ("vm_status", "time", "1 day"),
        ("system_logs", "time", "1 day"),
        ("backup_status", "time", "1 day"),
        ("system_updates", "time", "1 day"),
    ]

    try:
        async with get_async_session() as session:
            for table_name, time_column, chunk_interval in hypertables:
                try:
                    # Check if hypertable already exists
                    result = await session.execute(
                        text("""
                            SELECT table_name FROM timescaledb_information.hypertables 
                            WHERE table_name = :table_name
                        """),
                        {"table_name": table_name},
                    )

                    if result.fetchone():
                        results["skipped"].append(f"{table_name} (already exists)")
                        continue

                    # Create hypertable
                    await session.execute(
                        text(f"""
                            SELECT create_hypertable(
                                '{table_name}', 
                                '{time_column}', 
                                chunk_time_interval => INTERVAL '{chunk_interval}'
                            )
                        """)
                    )

                    await session.commit()
                    results["created"].append(table_name)
                    logger.info(f"Created hypertable: {table_name}")

                except Exception as e:
                    results["errors"].append(f"{table_name}: {str(e)}")
                    logger.error(f"Failed to create hypertable {table_name}: {e}")
                    await session.rollback()

    except Exception as e:
        logger.error(f"Failed to create hypertables: {e}")
        results["errors"].append(f"General error: {str(e)}")

    return results


async def setup_compression_policies() -> dict:
    """
    Set up compression policies for hypertables to optimize storage.

    Returns:
        dict: Results of compression policy setup
    """
    results = {"created": [], "skipped": [], "errors": []}

    # Define compression policies (compress data older than 7 days)
    compression_policies = [
        "system_metrics",
        "drive_health",
        "container_snapshots",
        "zfs_status",
        "zfs_snapshots",
        "network_interfaces",
        "docker_networks",
        "vm_status",
        "system_logs",
        "backup_status",
        "system_updates",
    ]

    try:
        async with get_async_session() as session:
            for table_name in compression_policies:
                try:
                    # Check if compression policy already exists
                    result = await session.execute(
                        text("""
                            SELECT hypertable_name FROM timescaledb_information.compression_settings 
                            WHERE hypertable_name = :table_name
                        """),
                        {"table_name": table_name},
                    )

                    if result.fetchone():
                        results["skipped"].append(f"{table_name} (policy exists)")
                        continue

                    # Enable compression on the hypertable
                    await session.execute(
                        text(f"ALTER TABLE {table_name} SET (timescaledb.compress)")
                    )

                    # Add compression policy (compress chunks older than 7 days)
                    await session.execute(
                        text(f"""
                            SELECT add_compression_policy('{table_name}', INTERVAL '7 days')
                        """)
                    )

                    await session.commit()
                    results["created"].append(table_name)
                    logger.info(f"Created compression policy: {table_name}")

                except Exception as e:
                    results["errors"].append(f"{table_name}: {str(e)}")
                    logger.error(f"Failed to create compression policy {table_name}: {e}")
                    await session.rollback()

    except Exception as e:
        logger.error(f"Failed to setup compression policies: {e}")
        results["errors"].append(f"General error: {str(e)}")

    return results


async def setup_retention_policies() -> dict:
    """
    Set up data retention policies for hypertables.

    Returns:
        dict: Results of retention policy setup
    """
    results = {"created": [], "skipped": [], "errors": []}

    settings = get_settings()

    # Define retention policies based on configuration
    retention_policies = [
        ("system_metrics", f"{settings.retention.retention_system_metrics_days} days"),
        ("drive_health", f"{settings.retention.retention_drive_health_days} days"),
        ("container_snapshots", f"{settings.retention.retention_container_snapshots_days} days"),
        ("zfs_status", "90 days"),
        ("zfs_snapshots", "90 days"),
        ("network_interfaces", "30 days"),
        ("docker_networks", "30 days"),
        ("vm_status", "30 days"),
        ("system_logs", "30 days"),
        ("backup_status", "90 days"),
        ("system_updates", "90 days"),
    ]

    try:
        async with get_async_session() as session:
            for table_name, retention_interval in retention_policies:
                try:
                    # Check if retention policy already exists
                    result = await session.execute(
                        text("""
                            SELECT hypertable FROM timescaledb_information.data_retention_policies 
                            WHERE hypertable = :table_name
                        """),
                        {"table_name": table_name},
                    )

                    if result.fetchone():
                        results["skipped"].append(f"{table_name} (policy exists)")
                        continue

                    # Add retention policy
                    await session.execute(
                        text(f"""
                            SELECT add_retention_policy('{table_name}', INTERVAL '{retention_interval}')
                        """)
                    )

                    await session.commit()
                    results["created"].append(f"{table_name} ({retention_interval})")
                    logger.info(f"Created retention policy: {table_name} - {retention_interval}")

                except Exception as e:
                    results["errors"].append(f"{table_name}: {str(e)}")
                    logger.error(f"Failed to create retention policy {table_name}: {e}")
                    await session.rollback()

    except Exception as e:
        logger.error(f"Failed to setup retention policies: {e}")
        results["errors"].append(f"General error: {str(e)}")

    return results


async def get_timescaledb_info() -> dict:
    """
    Get comprehensive TimescaleDB information and statistics.

    Returns:
        dict: TimescaleDB configuration and statistics
    """
    info = {
        "version": None,
        "license": None,
        "hypertables": [],
        "continuous_aggregates": [],
        "compression_stats": {},
        "retention_policies": [],
        "background_jobs": [],
    }

    try:
        async with get_async_session() as session:
            # TimescaleDB version
            result = await session.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
            )
            info["version"] = result.scalar()

            # License information
            try:
                result = await session.execute(text("SELECT timescaledb_license()"))
                info["license"] = result.scalar()
            except Exception:
                info["license"] = "community"

            # Hypertables information
            result = await session.execute(
                text("""
                    SELECT 
                        hypertable_name,
                        owner,
                        num_dimensions,
                        num_chunks,
                        compression_enabled,
                        tablespace
                    FROM timescaledb_information.hypertables
                    ORDER BY hypertable_name
                """)
            )
            info["hypertables"] = [dict(row) for row in result.fetchall()]

            # Continuous aggregates
            result = await session.execute(
                text("""
                    SELECT 
                        user_view_name,
                        materialized_only,
                        compression_enabled
                    FROM timescaledb_information.continuous_aggregates
                    ORDER BY user_view_name
                """)
            )
            info["continuous_aggregates"] = [dict(row) for row in result.fetchall()]

            # Compression statistics
            result = await session.execute(
                text("""
                    SELECT 
                        schema_name,
                        table_name,
                        compression_status,
                        uncompressed_heap_size,
                        uncompressed_index_size,
                        uncompressed_toast_size,
                        uncompressed_total_size,
                        compressed_heap_size,
                        compressed_index_size,
                        compressed_toast_size,
                        compressed_total_size
                    FROM timescaledb_information.compressed_hypertable_stats
                """)
            )
            compression_stats = result.fetchall()
            if compression_stats:
                info["compression_stats"] = [dict(row) for row in compression_stats]

            # Retention policies
            result = await session.execute(
                text("""
                    SELECT 
                        hypertable,
                        older_than,
                        cascade
                    FROM timescaledb_information.data_retention_policies
                    ORDER BY hypertable
                """)
            )
            info["retention_policies"] = [dict(row) for row in result.fetchall()]

            # Background jobs
            result = await session.execute(
                text("""
                    SELECT 
                        job_id,
                        application_name,
                        schedule_interval,
                        max_runtime,
                        max_retries,
                        retry_period,
                        proc_schema,
                        proc_name,
                        scheduled
                    FROM timescaledb_information.jobs
                    ORDER BY job_id
                """)
            )
            info["background_jobs"] = [dict(row) for row in result.fetchall()]

    except Exception as e:
        logger.error(f"Failed to get TimescaleDB info: {e}")
        info["error"] = str(e)

    return info


async def optimize_database() -> dict:
    """
    Perform database optimization operations.

    Returns:
        dict: Results of optimization operations
    """
    results = {"operations": [], "errors": []}

    try:
        async with get_async_session() as session:
            # Update table statistics
            try:
                await session.execute(text("ANALYZE"))
                await session.commit()
                results["operations"].append("Updated table statistics (ANALYZE)")
            except Exception as e:
                results["errors"].append(f"ANALYZE failed: {e}")

            # Vacuum unused space (light vacuum, non-blocking)
            try:
                await session.execute(text("VACUUM (ANALYZE)"))
                await session.commit()
                results["operations"].append("Performed VACUUM ANALYZE")
            except Exception as e:
                results["errors"].append(f"VACUUM failed: {e}")

            # Reorder continuous aggregates if any exist
            try:
                result = await session.execute(
                    text("SELECT user_view_name FROM timescaledb_information.continuous_aggregates")
                )
                caggs = result.fetchall()

                for cagg in caggs:
                    try:
                        await session.execute(
                            text(f"CALL refresh_continuous_aggregate('{cagg[0]}', NULL, NULL)")
                        )
                        results["operations"].append(f"Refreshed continuous aggregate: {cagg[0]}")
                    except Exception as e:
                        results["errors"].append(f"Failed to refresh {cagg[0]}: {e}")

                await session.commit()

            except Exception as e:
                results["errors"].append(f"Continuous aggregate refresh failed: {e}")

    except Exception as e:
        logger.error(f"Database optimization failed: {e}")
        results["errors"].append(f"General error: {str(e)}")

    return results


async def get_chunk_statistics() -> dict:
    """
    Get TimescaleDB chunk statistics for monitoring storage.

    Returns:
        dict: Chunk statistics and storage information
    """
    stats = {"total_chunks": 0, "compressed_chunks": 0, "chunk_details": [], "storage_summary": {}}

    try:
        async with get_async_session() as session:
            # Total chunk count
            result = await session.execute(
                text("SELECT COUNT(*) FROM timescaledb_information.chunks")
            )
            stats["total_chunks"] = result.scalar()

            # Compressed chunk count
            result = await session.execute(
                text("""
                    SELECT COUNT(*) FROM timescaledb_information.chunks
                    WHERE is_compressed = true
                """)
            )
            stats["compressed_chunks"] = result.scalar()

            # Detailed chunk information
            result = await session.execute(
                text("""
                    SELECT 
                        hypertable_name,
                        chunk_name,
                        range_start,
                        range_end,
                        is_compressed,
                        compressed_heap_size,
                        compressed_index_size,
                        uncompressed_heap_size,
                        uncompressed_index_size
                    FROM timescaledb_information.chunks
                    ORDER BY hypertable_name, range_start DESC
                    LIMIT 100
                """)
            )
            stats["chunk_details"] = [dict(row) for row in result.fetchall()]

            # Storage summary by hypertable
            result = await session.execute(
                text("""
                    SELECT 
                        hypertable_name,
                        COUNT(*) as chunk_count,
                        SUM(CASE WHEN is_compressed THEN 1 ELSE 0 END) as compressed_count,
                        pg_size_pretty(SUM(total_bytes)) as total_size
                    FROM timescaledb_information.chunks c
                    JOIN timescaledb_information.hypertables h ON c.hypertable_name = h.hypertable_name
                    GROUP BY hypertable_name
                    ORDER BY SUM(total_bytes) DESC
                """)
            )

            storage_summary = {}
            for row in result.fetchall():
                storage_summary[row[0]] = {
                    "chunk_count": row[1],
                    "compressed_count": row[2],
                    "total_size": row[3],
                }
            stats["storage_summary"] = storage_summary

    except Exception as e:
        logger.error(f"Failed to get chunk statistics: {e}")
        stats["error"] = str(e)

    return stats


async def validate_database_schema() -> dict:
    """
    Validate database schema integrity and consistency.

    Returns:
        dict: Schema validation results
    """
    validation = {
        "schema_valid": True,
        "tables_found": [],
        "missing_tables": [],
        "foreign_keys": [],
        "indexes": [],
        "extensions": [],
        "issues": [],
    }

    expected_tables = [
        "devices",
        "system_metrics",
        "drive_health",
        "container_snapshots",
        "zfs_status",
        "zfs_snapshots",
        "network_interfaces",
        "docker_networks",
        "vm_status",
        "system_logs",
        "backup_status",
        "system_updates",
    ]

    try:
        async with get_async_session() as session:
            # Check for required tables
            result = await session.execute(
                text("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
            )
            found_tables = [row[0] for row in result.fetchall()]
            validation["tables_found"] = found_tables

            # Find missing tables
            missing = set(expected_tables) - set(found_tables)
            validation["missing_tables"] = list(missing)

            if missing:
                validation["schema_valid"] = False
                validation["issues"].append(f"Missing tables: {', '.join(missing)}")

            # Check foreign key constraints
            result = await session.execute(
                text("""
                    SELECT 
                        tc.table_name,
                        tc.constraint_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public'
                    ORDER BY tc.table_name
                """)
            )
            validation["foreign_keys"] = [dict(row) for row in result.fetchall()]

            # Check indexes
            result = await session.execute(
                text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname
                """)
            )
            validation["indexes"] = [dict(row) for row in result.fetchall()]

            # Check required extensions
            result = await session.execute(
                text("""
                    SELECT extname, extversion FROM pg_extension 
                    WHERE extname IN ('timescaledb', 'uuid-ossp')
                    ORDER BY extname
                """)
            )
            validation["extensions"] = [dict(row) for row in result.fetchall()]

            # Validate TimescaleDB extension
            timescale_found = any(
                ext["extname"] == "timescaledb" for ext in validation["extensions"]
            )
            if not timescale_found:
                validation["schema_valid"] = False
                validation["issues"].append("TimescaleDB extension not installed")

    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        validation["schema_valid"] = False
        validation["issues"].append(f"Validation error: {str(e)}")

    return validation


async def get_connection_info() -> dict:
    """
    Get current database connection information.

    Returns:
        dict: Connection details and configuration
    """
    info = {}

    try:
        settings = get_settings()
        engine = get_async_engine()

        info["configuration"] = {
            "host": settings.database.postgres_host,
            "port": settings.database.postgres_port,
            "database": settings.database.postgres_db,
            "user": settings.database.postgres_user,
            "pool_size": settings.database.db_pool_size,
            "max_overflow": settings.database.db_max_overflow,
        }

        # Pool information
        pool = engine.pool
        info["pool_status"] = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
        }

        # Current database session info
        async with get_async_session() as session:
            result = await session.execute(
                text("""
                    SELECT 
                        current_database() as database,
                        current_user as user,
                        inet_server_addr() as server_addr,
                        inet_server_port() as server_port,
                        version() as server_version
                """)
            )
            db_info = result.fetchone()

            info["server_info"] = {
                "database": db_info[0],
                "user": db_info[1],
                "server_addr": db_info[2],
                "server_port": db_info[3],
                "version": db_info[4],
            }

    except Exception as e:
        logger.error(f"Failed to get connection info: {e}")
        info["error"] = str(e)

    return info
