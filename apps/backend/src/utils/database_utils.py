"""
Database Utilities - Infrastructor Project

Reusable utilities to eliminate database session management redundancy
and provide consistent error handling patterns.
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, TypeVar, Union
import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from apps.backend.src.core.exceptions import DatabaseOperationError
from apps.backend.src.models.device import Device
from apps.backend.src.services.device_service import DeviceService

logger = logging.getLogger(__name__)

T = TypeVar('T')


@asynccontextmanager
async def database_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions with automatic cleanup.
    
    Usage:
        async with database_session(session_factory) as session:
            # Use session here
            result = await session.execute(query)
    
    Args:
        session_factory: Async session factory
        
    Yields:
        AsyncSession: Database session
        
    Raises:
        DatabaseOperationError: On session creation or cleanup errors
    """
    session = None
    try:
        session = session_factory()
        yield session
        await session.commit()
    except SQLAlchemyError as e:
        if session:
            await session.rollback()
        logger.error(f"Database session error: {e}")
        raise DatabaseOperationError(f"Database operation failed: {str(e)}") from e
    except Exception as e:
        if session:
            await session.rollback()
        logger.error(f"Unexpected session error: {e}")
        raise DatabaseOperationError(f"Unexpected database error: {str(e)}") from e
    finally:
        if session:
            await session.close()


async def with_database_session(
    session_factory: async_sessionmaker[AsyncSession],
    operation: Callable[[AsyncSession], Any]
) -> Any:
    """
    Execute a database operation with automatic session management.
    
    Usage:
        async def my_operation(session: AsyncSession):
            return await session.execute(query)
        
        result = await with_database_session(session_factory, my_operation)
    
    Args:
        session_factory: Async session factory
        operation: Async function that takes a session and returns a result
        
    Returns:
        Result of the operation
        
    Raises:
        DatabaseOperationError: On database errors
    """
    async with database_session(session_factory) as session:
        return await operation(session)


async def get_device_with_session(
    session_factory: async_sessionmaker[AsyncSession],
    hostname: str
) -> Device:
    """
    Get device by hostname with automatic session management.
    Common pattern used throughout the codebase.
    
    Args:
        session_factory: Async session factory
        hostname: Device hostname
        
    Returns:
        Device object
        
    Raises:
        DatabaseOperationError: On database errors
    """
    async def operation(session: AsyncSession) -> Device:
        device_service = DeviceService(session)
        return await device_service.get_device_by_hostname(hostname)
    
    return await with_database_session(session_factory, operation)


async def get_device_id_by_hostname(
    session_factory: async_sessionmaker[AsyncSession],
    hostname: str
) -> UUID:
    """
    Get device ID by hostname with automatic session management.
    Another common pattern used throughout the codebase.
    
    Args:
        session_factory: Async session factory
        hostname: Device hostname
        
    Returns:
        Device UUID
        
    Raises:
        DatabaseOperationError: On database errors
    """
    device = await get_device_with_session(session_factory, hostname)
    return device.id


@asynccontextmanager
async def device_operation_context(
    session_factory: async_sessionmaker[AsyncSession],
    hostname: str
) -> AsyncGenerator[tuple[AsyncSession, Device, UUID], None]:
    """
    Context manager that provides session, device, and device_id for operations.
    Eliminates the most common pattern in the codebase.
    
    Usage:
        async with device_operation_context(session_factory, hostname) as (session, device, device_id):
            # Use session, device, and device_id
            pass
    
    Args:
        session_factory: Async session factory
        hostname: Device hostname
        
    Yields:
        tuple: (session, device, device_id)
        
    Raises:
        DatabaseOperationError: On database errors
    """
    async with database_session(session_factory) as session:
        device_service = DeviceService(session)
        device = await device_service.get_device_by_hostname(hostname)
        yield session, device, device.id


async def query_devices_with_tags(
    session_factory: async_sessionmaker[AsyncSession],
    tag_conditions: dict[str, Any],
    monitoring_enabled: bool = True
) -> list[Device]:
    """
    Query devices with specific tag conditions and monitoring status.
    Common pattern for finding devices with specific capabilities.
    
    Args:
        session_factory: Async session factory
        tag_conditions: Dictionary of tag conditions to match
        monitoring_enabled: Whether to filter for monitoring-enabled devices
        
    Returns:
        List of matching devices
        
    Raises:
        DatabaseOperationError: On database errors
    """
    async def operation(session: AsyncSession) -> list[Device]:
        from sqlalchemy import and_
        
        conditions = []
        if monitoring_enabled:
            conditions.append(Device.monitoring_enabled == True)
            
        # Add tag conditions
        for tag_key, tag_value in tag_conditions.items():
            if isinstance(tag_value, bool):
                # For boolean values, check both existence and value
                conditions.extend([
                    Device.tags.op("?")({tag_key}),  # Key exists
                    Device.tags[tag_key].astext.cast(bool) == tag_value  # Value matches
                ])
            else:
                # For other values, just check key existence
                conditions.append(Device.tags.op("?")(tag_key))
        
        result = await session.execute(select(Device).where(and_(*conditions)))
        return result.scalars().all()
    
    return await with_database_session(session_factory, operation)


class DatabaseOperationHelper:
    """
    Helper class for common database operations with consistent error handling.
    Reduces boilerplate code across the application.
    """
    
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory
    
    async def get_device_by_hostname(self, hostname: str) -> Device:
        """Get device by hostname."""
        return await get_device_with_session(self.session_factory, hostname)
    
    async def get_device_id_by_hostname(self, hostname: str) -> UUID:
        """Get device ID by hostname."""
        return await get_device_id_by_hostname(self.session_factory, hostname)
    
    async def query_devices_with_tags(
        self, 
        tag_conditions: dict[str, Any], 
        monitoring_enabled: bool = True
    ) -> list[Device]:
        """Query devices with tag conditions."""
        return await query_devices_with_tags(
            self.session_factory, tag_conditions, monitoring_enabled
        )
    
    async def execute_query(self, query_operation: Callable[[AsyncSession], Any]) -> Any:
        """Execute custom query operation."""
        return await with_database_session(self.session_factory, query_operation)
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session context manager."""
        async with database_session(self.session_factory) as session:
            yield session
    
    @asynccontextmanager
    async def device_context(self, hostname: str) -> AsyncGenerator[tuple[AsyncSession, Device, UUID], None]:
        """Get device operation context."""
        async with device_operation_context(self.session_factory, hostname) as context:
            yield context


def get_database_helper(session_factory: async_sessionmaker[AsyncSession]) -> DatabaseOperationHelper:
    """
    Factory function to create DatabaseOperationHelper instance.
    
    Args:
        session_factory: Async session factory
        
    Returns:
        DatabaseOperationHelper instance
    """
    return DatabaseOperationHelper(session_factory)