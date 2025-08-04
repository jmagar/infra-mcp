#!/usr/bin/env python3
"""
Test script for Phase 1 SQLAlchemy models.

This script tests:
1. Model creation and basic properties
2. Relationships between models
3. CRUD operations
4. Database constraints and validation
"""

import asyncio
import sys
from datetime import datetime, timezone
from uuid import uuid4
from decimal import Decimal

# Add the project path to sys.path
sys.path.append('/home/jmagar/code/infrastructor/apps/backend/src')

from core.database import init_database, get_async_session, close_database
from models.device import Device
from models.audit import DataCollectionAudit
from models.configuration import ConfigurationSnapshot, ConfigurationChangeEvent
from models.performance import ServicePerformanceMetric
from models.cache import CacheMetadata


async def test_device_model():
    """Test Device model creation and basic properties."""
    print("🧪 Testing Device model...")
    
    async with get_async_session() as session:
        # Create a test device
        device = Device(
            hostname="test-server-001",
            device_type="server",
            description="Test server for model validation",
            location="datacenter-a",
            device_metadata={"os": "Ubuntu 22.04", "role": "web-server"},
            tags={"environment": "test", "team": "infrastructure"},
            docker_compose_path="/opt/docker-compose.yml",
            docker_appdata_path="/opt/appdata",
            monitoring_enabled=True,
            status="online",
            last_collection_status="success",
            collection_error_count=0
        )
        
        session.add(device)
        await session.commit()
        await session.refresh(device)
        
        print(f"   ✅ Created device: {device.hostname} (ID: {device.id})")
        print(f"   ✅ Device metadata: {device.device_metadata}")
        print(f"   ✅ Device tags: {device.tags}")
        
        return device


async def test_audit_model(device: Device):
    """Test DataCollectionAudit model creation and relationship."""
    print("🧪 Testing DataCollectionAudit model...")
    
    async with get_async_session() as session:
        # Create audit record
        audit = DataCollectionAudit(
            time=datetime.now(timezone.utc),
            device_id=device.id,
            data_type="system_metrics",
            collection_method="ssh",
            collection_source="polling_service",
            force_refresh=False,
            cache_hit=True,
            duration_ms=250,
            ssh_command_count=3,
            data_size_bytes=1024,
            status="success",
            records_created=5,
            records_updated=0,
            freshness_threshold=300
        )
        
        session.add(audit)
        await session.commit()
        await session.refresh(audit)
        
        print(f"   ✅ Created audit record: {audit.operation_id}")
        print(f"   ✅ Data type: {audit.data_type}, Status: {audit.status}")
        print(f"   ✅ Duration: {audit.duration_ms}ms, Cache hit: {audit.cache_hit}")
        
        return audit


async def test_configuration_models(device: Device):
    """Test ConfigurationSnapshot and ConfigurationChangeEvent models."""
    print("🧪 Testing Configuration models...")
    
    async with get_async_session() as session:
        # Create configuration snapshot
        snapshot = ConfigurationSnapshot(
            time=datetime.now(timezone.utc),
            device_id=device.id,
            config_type="docker_compose",
            file_path="/opt/docker-compose.yml",
            content_hash="abc123def456",
            file_size_bytes=2048,
            raw_content="version: '3.8'\nservices:\n  web:\n    image: nginx",
            parsed_data={"version": "3.8", "services": {"web": {"image": "nginx"}}},
            change_type="modified",
            previous_hash="xyz789uvw012",
            file_modified_time=datetime.now(timezone.utc),
            collection_source="file_watcher",
            detection_latency_ms=50,
            affected_services=["web", "proxy"],
            requires_restart=True,
            risk_level="MEDIUM"
        )
        
        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)
        
        print(f"   ✅ Created configuration snapshot: {snapshot.id}")
        print(f"   ✅ Config type: {snapshot.config_type}, Change: {snapshot.change_type}")
        print(f"   ✅ Risk level: {snapshot.risk_level}, Requires restart: {snapshot.requires_restart}")
        
        # Create configuration change event
        change_event = ConfigurationChangeEvent(
            time=datetime.now(timezone.utc),
            device_id=device.id,
            snapshot_id=snapshot.id,
            config_type="docker_compose",
            file_path="/opt/docker-compose.yml",
            change_type="modified",
            affected_services=["web", "proxy"],
            service_dependencies=["database"],
            requires_restart=True,
            restart_services=["web"],
            changes_summary={"services.web.image": {"old": "nginx:1.20", "new": "nginx:1.21"}},
            risk_level="MEDIUM",
            confidence_score=Decimal("0.85"),
            processed=False,
            notifications_sent=["email", "slack"]
        )
        
        session.add(change_event)
        await session.commit()
        await session.refresh(change_event)
        
        print(f"   ✅ Created change event: {change_event.id}")
        print(f"   ✅ Confidence score: {change_event.confidence_score}")
        print(f"   ✅ Notifications sent: {change_event.notifications_sent}")
        
        return snapshot, change_event


async def test_performance_model():
    """Test ServicePerformanceMetric model."""
    print("🧪 Testing ServicePerformanceMetric model...")
    
    async with get_async_session() as session:
        # Create performance metric
        metric = ServicePerformanceMetric(
            time=datetime.now(timezone.utc),
            service_name="polling_service",
            operations_total=100,
            operations_successful=95,
            operations_failed=5,
            avg_duration_ms=Decimal("250.500"),
            min_duration_ms=Decimal("100.000"),
            max_duration_ms=Decimal("800.000"),
            p95_duration_ms=Decimal("650.000"),
            p99_duration_ms=Decimal("750.000"),
            cache_hit_count=80,
            cache_miss_count=20,
            error_count=5,
            timeout_count=2,
            retry_count=3,
            throughput_ops_per_sec=Decimal("4.000"),
            concurrent_operations=5,
            memory_usage_bytes=104857600,  # 100MB
            cpu_usage_percent=Decimal("15.50"),
            network_io_bytes=1048576,  # 1MB
            disk_io_bytes=2097152,  # 2MB
            metadata={"version": "1.0.0", "node": "worker-1"}
        )
        
        session.add(metric)
        await session.commit()
        await session.refresh(metric)
        
        print(f"   ✅ Created performance metric for service: {metric.service_name}")
        print(f"   ✅ Operations: {metric.operations_successful}/{metric.operations_total} successful")
        print(f"   ✅ Avg duration: {metric.avg_duration_ms}ms, Throughput: {metric.throughput_ops_per_sec} ops/sec")
        print(f"   ✅ Cache hit rate: {metric.cache_hit_count/(metric.cache_hit_count + metric.cache_miss_count)*100:.1f}%")
        
        return metric


async def test_cache_model(device: Device):
    """Test CacheMetadata model."""
    print("🧪 Testing CacheMetadata model...")
    
    async with get_async_session() as session:
        # Create cache metadata
        cache = CacheMetadata(
            device_id=device.id,
            cache_key="system_metrics:test-server-001",
            data_type="system_metrics",
            expires_at=datetime.now(timezone.utc),
            last_accessed=datetime.now(timezone.utc),
            access_count=50,
            hit_count=45,
            miss_count=5,
            data_size_bytes=4096,
            ttl_seconds=300,
            is_active=True,
            metadata={"compression": "gzip", "version": "v1"}
        )
        
        session.add(cache)
        await session.commit()
        await session.refresh(cache)
        
        print(f"   ✅ Created cache metadata: {cache.id}")
        print(f"   ✅ Cache key: {cache.cache_key}")
        print(f"   ✅ Hit rate: {cache.hit_count/(cache.hit_count + cache.miss_count)*100:.1f}%")
        print(f"   ✅ Data size: {cache.data_size_bytes} bytes, TTL: {cache.ttl_seconds}s")
        
        return cache


async def test_relationships(device: Device):
    """Test relationships between models."""
    print("🧪 Testing model relationships...")
    
    async with get_async_session() as session:
        # Query device with relationships
        from sqlalchemy.orm import selectinload
        from sqlalchemy import select
        
        result = await session.execute(
            select(Device)
            .options(
                selectinload(Device.data_collection_audits),
                selectinload(Device.configuration_snapshots),
                selectinload(Device.configuration_change_events),
                selectinload(Device.cache_metadata)
            )
            .where(Device.id == device.id)
        )
        loaded_device = result.scalar_one()
        
        print(f"   ✅ Device loaded: {loaded_device.hostname}")
        print(f"   ✅ Audit records: {len(loaded_device.data_collection_audits)}")
        print(f"   ✅ Configuration snapshots: {len(loaded_device.configuration_snapshots)}")
        print(f"   ✅ Configuration change events: {len(loaded_device.configuration_change_events)}")
        print(f"   ✅ Cache metadata records: {len(loaded_device.cache_metadata)}")
        
        # Test reverse relationships
        if loaded_device.data_collection_audits:
            audit = loaded_device.data_collection_audits[0]
            print(f"   ✅ Audit->Device relationship: {audit.device.hostname}")
        
        if loaded_device.configuration_snapshots:
            snapshot = loaded_device.configuration_snapshots[0]
            print(f"   ✅ Config->Device relationship: {snapshot.device.hostname}")


async def test_crud_operations():
    """Test basic CRUD operations."""
    print("🧪 Testing CRUD operations...")
    
    async with get_async_session() as session:
        from sqlalchemy import select, update, delete
        
        # READ: Query all devices
        result = await session.execute(select(Device))
        devices = result.scalars().all()
        print(f"   ✅ READ: Found {len(devices)} devices")
        
        if devices:
            device = devices[0]
            original_description = device.description
            
            # UPDATE: Modify device description
            await session.execute(
                update(Device)
                .where(Device.id == device.id)
                .values(description="Updated test description")
            )
            await session.commit()
            
            # Verify update
            result = await session.execute(select(Device).where(Device.id == device.id))
            updated_device = result.scalar_one()
            print(f"   ✅ UPDATE: Description changed from '{original_description}' to '{updated_device.description}'")
            
            # COUNT: Count audit records for this device
            from sqlalchemy import func
            result = await session.execute(
                select(func.count(DataCollectionAudit.operation_id))
                .where(DataCollectionAudit.device_id == device.id)
            )
            audit_count = result.scalar()
            print(f"   ✅ COUNT: Device has {audit_count} audit records")


async def main():
    """Main test function."""
    print("🚀 Starting Phase 1 SQLAlchemy Model Tests\n")
    
    try:
        # Initialize database connection
        await init_database()
        print("✅ Database connection initialized\n")
        
        # Test each model
        device = await test_device_model()
        print()
        
        audit = await test_audit_model(device)
        print()
        
        snapshot, change_event = await test_configuration_models(device)
        print()
        
        metric = await test_performance_model()
        print()
        
        cache = await test_cache_model(device)
        print()
        
        # Test relationships
        await test_relationships(device)
        print()
        
        # Test CRUD operations
        await test_crud_operations()
        print()
        
        print("🎉 All model tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Close database connections
        await close_database()
        print("✅ Database connections closed")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)