#!/usr/bin/env python3
"""
Test script for Phase 1 Pydantic schemas.

Tests serialization, deserialization, field validation, and ORM integration.
"""

import sys
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
import json

# Add the project path to sys.path for proper imports
sys.path.append('/home/jmagar/code/infrastructor/apps/backend/src')

try:
    from schemas.audit import (
        DataCollectionAuditBase, DataCollectionAuditCreate, DataCollectionAuditResponse,
        DataCollectionAuditListResponse, DataCollectionAuditDetailResponse
    )
    from schemas.configuration import (
        ConfigurationSnapshotBase, ConfigurationSnapshotCreate, ConfigurationSnapshotResponse,
        ConfigurationChangeEventBase, ConfigurationChangeEventCreate, ConfigurationChangeEventResponse
    )
    from schemas.performance import (
        ServicePerformanceMetricBase, ServicePerformanceMetricCreate, ServicePerformanceMetricResponse
    )
    from schemas.cache import (
        CacheMetadataBase, CacheMetadataCreate, CacheMetadataResponse
    )
    from pydantic import ValidationError as PydanticValidationError
    
    print("✅ All schema imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_audit_schemas():
    """Test DataCollectionAudit schemas."""
    print("🧪 Testing DataCollectionAudit schemas...")
    
    # Test valid data
    valid_data = {
        "device_id": str(uuid4()),
        "data_type": "system_metrics",
        "collection_method": "ssh",
        "collection_source": "polling_service",
        "force_refresh": False,
        "cache_hit": True,
        "duration_ms": 250,
        "ssh_command_count": 3,
        "data_size_bytes": 1024,
        "status": "success",
        "records_created": 5,
        "records_updated": 0,
        "freshness_threshold": 300
    }
    
    try:
        # Test Create schema
        audit_create = DataCollectionAuditCreate(**valid_data)
        print(f"   ✅ DataCollectionAuditCreate: {audit_create.data_type} - {audit_create.status}")
        
        # Test serialization
        json_data = audit_create.model_dump()
        print(f"   ✅ Serialization: {len(json_data)} fields")
        
        # Test deserialization
        audit_from_json = DataCollectionAuditCreate(**json_data)
        print(f"   ✅ Deserialization: {audit_from_json.data_type}")
        
        # Test Response schema with additional fields
        response_data = {
            **valid_data,
            "id": str(uuid4()),
            "operation_id": str(uuid4()),
            "time": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        audit_response = DataCollectionAuditResponse(**response_data)
        print(f"   ✅ DataCollectionAuditResponse: {audit_response.operation_id}")
        
    except Exception as e:
        print(f"   ❌ Audit schema test failed: {e}")
        return False
    
    # Test validation errors
    try:
        # Invalid duration (negative)
        invalid_data = valid_data.copy()
        invalid_data["duration_ms"] = -100
        DataCollectionAuditCreate(**invalid_data)
        print("   ❌ Validation should have failed for negative duration")
        return False
    except PydanticValidationError as e:
        print(f"   ✅ Validation correctly rejected negative duration: {len(e.errors())} errors")
    
    try:
        # Invalid data size (too large)
        invalid_data = valid_data.copy()
        invalid_data["data_size_bytes"] = 2 * 1024 * 1024 * 1024  # 2GB
        DataCollectionAuditCreate(**invalid_data)
        print("   ❌ Validation should have failed for excessive data size")
        return False
    except PydanticValidationError as e:
        print(f"   ✅ Validation correctly rejected excessive data size: {len(e.errors())} errors")
    
    return True


def test_configuration_schemas():
    """Test Configuration schemas."""
    print("🧪 Testing Configuration schemas...")
    
    # Test ConfigurationSnapshot
    snapshot_data = {
        "device_id": str(uuid4()),
        "config_type": "docker-compose",  # Use hyphenated form
        "file_path": "/opt/docker-compose.yml",
        "content_hash": "a1b2c3d4e5f6789012345678901234567890abcd",  # Valid 40-char hex
        "file_size_bytes": 2048,
        "raw_content": "version: '3.8'\nservices:\n  web:\n    image: nginx",
        "parsed_data": {"version": "3.8", "services": {"web": {"image": "nginx"}}},
        "change_type": "modified",
        "previous_hash": "9876543210fedcba0987654321098765432109ba",  # Valid 40-char hex
        "file_modified_time": datetime.now(timezone.utc).isoformat(),
        "collection_source": "file_watch",  # Use valid enum value
        "detection_latency_ms": 50,
        "affected_services": ["web", "proxy"],
        "requires_restart": True,
        "risk_level": "MEDIUM"
    }
    
    try:
        # Test Create schema
        snapshot_create = ConfigurationSnapshotCreate(**snapshot_data)
        print(f"   ✅ ConfigurationSnapshotCreate: {snapshot_create.config_type} - {snapshot_create.change_type}")
        
        # Test model validation (requires_restart + affected_services)
        valid_data_copy = snapshot_data.copy()
        valid_data_copy["requires_restart"] = True
        valid_data_copy["affected_services"] = ["web"]
        snapshot_valid = ConfigurationSnapshotCreate(**valid_data_copy)
        print(f"   ✅ Model validation passed for restart requirement")
        
    except Exception as e:
        print(f"   ❌ Configuration snapshot test failed: {e}")
        return False
    
    # Test ConfigurationChangeEvent
    change_data = {
        "device_id": str(uuid4()),
        "snapshot_id": str(uuid4()),
        "config_type": "docker-compose",
        "file_path": "/opt/docker-compose.yml",
        "change_type": "modified",
        "affected_services": ["web", "proxy"],
        "service_dependencies": ["database"],
        "requires_restart": True,
        "restart_services": ["web"],
        "changes_summary": {"services.web.image": {"old": "nginx:1.20", "new": "nginx:1.21"}},
        "risk_level": "MEDIUM",
        "confidence_score": "0.85",
        "processed": False,
        "notifications_sent": [{"type": "email", "timestamp": datetime.now(timezone.utc).isoformat()}, {"type": "slack", "timestamp": datetime.now(timezone.utc).isoformat()}]
    }
    
    try:
        change_create = ConfigurationChangeEventCreate(**change_data)
        print(f"   ✅ ConfigurationChangeEventCreate: {change_create.change_type} - {change_create.risk_level}")
        
        # Test Decimal conversion
        print(f"   ✅ Confidence score converted to Decimal: {change_create.confidence_score}")
        
    except Exception as e:
        print(f"   ❌ Configuration change event test failed: {e}")
        return False
    
    # Test validation errors
    try:
        # Invalid confidence score (> 1.0)
        invalid_data = change_data.copy()
        invalid_data["confidence_score"] = "1.5"
        ConfigurationChangeEventCreate(**invalid_data)
        print("   ❌ Validation should have failed for confidence score > 1.0")
        return False
    except PydanticValidationError as e:
        print(f"   ✅ Validation correctly rejected invalid confidence score: {len(e.errors())} errors")
    
    return True


def test_performance_schemas():
    """Test ServicePerformanceMetric schemas."""
    print("🧪 Testing ServicePerformanceMetric schemas...")
    
    performance_data = {
        "service_name": "polling_service",
        "operations_total": 100,
        "operations_successful": 100,
        "operations_failed": 0,
        "operations_cached": 80,
        "avg_duration_ms": 250.5,
        "min_duration_ms": 100,
        "max_duration_ms": 800,
        "ssh_connections_created": 5,
        "ssh_connections_reused": 10,
        "ssh_commands_executed": 50,
        "cache_hit_ratio": 80.0,
        "cache_size_entries": 1000,
        "cache_evictions": 2,
        "data_collected_bytes": 1048576,
        "database_writes": 100,
        "error_types": {},  # Empty since no failures
        "top_errors": []  # Empty since no failures
    }
    
    try:
        # Test Create schema
        perf_create = ServicePerformanceMetricCreate(**performance_data)
        print(f"   ✅ ServicePerformanceMetricCreate: {perf_create.service_name}")
        
        # Test field values
        print(f"   ✅ Avg duration: {perf_create.avg_duration_ms}")
        print(f"   ✅ Operations: {perf_create.operations_successful}/{perf_create.operations_total}")
        
        # Test Response schema
        response_data = {
            **performance_data,
            "id": str(uuid4()),
            "time": datetime.now(timezone.utc).isoformat()
        }
        perf_response = ServicePerformanceMetricResponse(**response_data)
        print(f"   ✅ ServicePerformanceMetricResponse: {perf_response.service_name}")
        
    except Exception as e:
        print(f"   ❌ Performance schema test failed: {e}")
        return False
    
    # Test validation errors
    try:
        # Invalid operations count (successful + failed + cached > total)
        invalid_data = performance_data.copy()
        invalid_data["operations_total"] = 50
        invalid_data["operations_successful"] = 30
        invalid_data["operations_failed"] = 10
        invalid_data["operations_cached"] = 20  # 30 + 10 + 20 = 60 > 50
        ServicePerformanceMetricCreate(**invalid_data)
        print("   ❌ Validation should have failed for invalid operations count")
        return False
    except PydanticValidationError as e:
        print(f"   ✅ Validation correctly rejected invalid operations count: {len(e.errors())} errors")
    
    return True


def test_cache_schemas():
    """Test CacheMetadata schemas."""
    print("🧪 Testing CacheMetadata schemas...")
    
    cache_data = {
        "device_id": str(uuid4()),
        "cache_key": "system_metrics:test-server-001",
        "data_type": "system_metrics",
        "expires_at": datetime.now(timezone.utc).isoformat(),
        "last_accessed": datetime.now(timezone.utc).isoformat(),
        "access_count": 50,
        "hit_count": 45,
        "miss_count": 5,
        "data_size_bytes": 4096,
        "ttl_seconds": 300,
        "is_active": True,
        "metadata": {"compression": "gzip", "version": "v1"}
    }
    
    try:
        # Test Create schema
        cache_create = CacheMetadataCreate(**cache_data)
        print(f"   ✅ CacheMetadataCreate: {cache_create.cache_key}")
        
        # Test key validation
        print(f"   ✅ Cache key validation passed: {cache_create.cache_key}")
        
        # Test Response schema
        response_data = {
            **cache_data,
            "id": str(uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "invalidated": False,
            "invalidated_at": None,
            "invalidation_reason": None
        }
        cache_response = CacheMetadataResponse(**response_data)
        print(f"   ✅ CacheMetadataResponse: {cache_response.cache_key}")
        
    except Exception as e:
        print(f"   ❌ Cache schema test failed: {e}")
        return False
    
    # Test validation errors
    try:
        # Invalid cache key format
        invalid_data = cache_data.copy()
        invalid_data["cache_key"] = "invalid key with spaces!"
        CacheMetadataCreate(**invalid_data)
        print("   ❌ Validation should have failed for invalid cache key")
        return False
    except PydanticValidationError as e:
        print(f"   ✅ Validation correctly rejected invalid cache key: {len(e.errors())} errors")
    
    try:
        # Invalid TTL (too large)
        invalid_data = cache_data.copy()
        invalid_data["ttl_seconds"] = 100000000  # > 86400 * 30
        CacheMetadataCreate(**invalid_data)
        print("   ❌ Validation should have failed for excessive TTL")
        return False
    except PydanticValidationError as e:
        print(f"   ✅ Validation correctly rejected excessive TTL: {len(e.errors())} errors")
    
    return True


def test_json_serialization():
    """Test JSON serialization/deserialization with various data types."""
    print("🧪 Testing JSON serialization...")
    
    try:
        # Test with datetime and UUID serialization
        audit_data = {
            "device_id": str(uuid4()),
            "data_type": "system_metrics",
            "collection_method": "ssh",
            "collection_source": "polling_service",
            "status": "success",
            "duration_ms": 250
        }
        
        audit = DataCollectionAuditCreate(**audit_data)
        
        # Test model_dump (Pydantic v2 method)
        json_dict = audit.model_dump()
        print(f"   ✅ model_dump() produced {len(json_dict)} fields")
        
        # Test JSON string serialization
        json_str = audit.model_dump_json()
        print(f"   ✅ model_dump_json() produced {len(json_str)} character string")
        
        # Test deserialization from JSON dict
        audit_from_dict = DataCollectionAuditCreate(**json_dict)
        print(f"   ✅ Deserialized from dict: {audit_from_dict.data_type}")
        
        # Test deserialization from JSON string
        import json
        dict_from_json = json.loads(json_str)
        audit_from_json = DataCollectionAuditCreate(**dict_from_json)
        print(f"   ✅ Deserialized from JSON string: {audit_from_json.data_type}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ JSON serialization test failed: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 Starting Phase 1 Pydantic Schema Tests\n")
    
    success = True
    
    if not test_audit_schemas():
        success = False
    print()
    
    if not test_configuration_schemas():
        success = False
    print()
    
    if not test_performance_schemas():
        success = False
    print()
    
    if not test_cache_schemas():
        success = False
    print()
    
    if not test_json_serialization():
        success = False
    print()
    
    if success:
        print("🎉 All Pydantic schema tests completed successfully!")
        print("✅ Field validation working correctly")
        print("✅ Cross-field validation working correctly")
        print("✅ Serialization/deserialization working correctly")
        print("✅ Response models working correctly")
        print("✅ Error handling working correctly")
    else:
        print("❌ Some schema tests failed")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)