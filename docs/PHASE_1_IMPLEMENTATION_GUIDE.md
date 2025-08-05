# Phase 1, Part 1: Database Schema & API Contracts - Detailed Implementation Guide

This guide provides a complete, step-by-step implementation plan for the database schema overhaul and the corresponding API schema (Pydantic models) refactoring, as outlined in the main `IMPLEMENTATION_GUIDE.md`.

---

## **Part 1.A: Database Schema Overhaul (SQL & SQLAlchemy)**

### **Step 1: Create Comprehensive New TimescaleDB Hypertables Schema**

**Objective**: Establish a single, authoritative SQL schema for the entire database, including existing and new tables, for a complete "fresh start" reset.

**Implementation**: Create a new SQL script in the `apps/backend/init-scripts/` directory. This script will be the **single source of truth** for the database schema and will be executed as part of the database initialization process, replacing any previous schema scripts.

```sql
-- file: apps/backend/init-scripts/02-unified-schema.sql

-- =================================================================
-- Existing Tables (Rewritten for Unified Architecture)
-- =================================================================

-- Device Registry
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hostname VARCHAR(255) UNIQUE NOT NULL,
    device_type VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- System Metrics Hypertable
CREATE TABLE IF NOT EXISTS system_metrics (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    cpu_usage FLOAT,
    memory_usage FLOAT,
    disk_io JSONB,
    network_traffic JSONB,
    PRIMARY KEY (time, device_id)
);

-- Container Snapshots Hypertable
CREATE TABLE IF NOT EXISTS container_snapshots (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    container_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    image VARCHAR(255),
    status VARCHAR(50),
    cpu_usage FLOAT,
    memory_usage_bytes BIGINT,
    PRIMARY KEY (time, device_id, container_id)
);

-- Drive Health Hypertable
CREATE TABLE IF NOT EXISTS drive_health (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    drive_name VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    serial_number VARCHAR(255),
    smart_attributes JSONB,
    temperature_celsius INTEGER,
    power_on_hours INTEGER,
    is_healthy BOOLEAN,
    PRIMARY KEY (time, device_id, drive_name)
);


-- =================================================================
-- New Tables for Unified Architecture
-- =================================================================

-- 1. Data Collection Audit Table
CREATE TABLE IF NOT EXISTS data_collection_audit (
    time TIMESTAMPTZ NOT NULL,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    operation_id UUID NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    collection_method VARCHAR(50) NOT NULL,
    collection_source VARCHAR(100),
    force_refresh BOOLEAN DEFAULT FALSE,
    cache_hit BOOLEAN DEFAULT FALSE,
    duration_ms INTEGER,
    ssh_command_count INTEGER DEFAULT 0,
    data_size_bytes BIGINT,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    warnings JSONB,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    freshness_threshold INTEGER,
    PRIMARY KEY (time, device_id, operation_id)
);

-- 2. Configuration Snapshots Table
CREATE TABLE IF NOT EXISTS configuration_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    time TIMESTAMPTZ NOT NULL,
    config_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    file_size_bytes INTEGER,
    raw_content TEXT NOT NULL,
    parsed_data JSONB,
    change_type VARCHAR(20) NOT NULL,
    previous_hash VARCHAR(64),
    file_modified_time TIMESTAMPTZ,
    collection_source VARCHAR(50) NOT NULL,
    detection_latency_ms INTEGER,
    affected_services JSONB,
    requires_restart BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20) DEFAULT 'MEDIUM'
);

-- 3. Configuration Change Events Table
CREATE TABLE IF NOT EXISTS configuration_change_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    snapshot_id UUID NOT NULL REFERENCES configuration_snapshots(id) ON DELETE CASCADE,
    time TIMESTAMPTZ NOT NULL,
    config_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    change_type VARCHAR(20) NOT NULL,
    affected_services JSONB,
    service_dependencies JSONB,
    requires_restart BOOLEAN DEFAULT FALSE,
    restart_services JSONB,
    changes_summary JSONB,
    risk_level VARCHAR(20) DEFAULT 'MEDIUM',
    confidence_score NUMERIC(3, 2),
    processed BOOLEAN DEFAULT FALSE,
    notifications_sent JSONB
);

-- 4. Service Performance Metrics Table
CREATE TABLE IF NOT EXISTS service_performance_metrics (
    time TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(50) NOT NULL,
    operations_total INTEGER DEFAULT 0,
    operations_successful INTEGER DEFAULT 0,
    operations_failed INTEGER DEFAULT 0,
    operations_cached INTEGER DEFAULT 0,
    avg_duration_ms NUMERIC(8, 2),
    max_duration_ms INTEGER,
    min_duration_ms INTEGER,
    ssh_connections_created INTEGER DEFAULT 0,
    ssh_connections_reused INTEGER DEFAULT 0,
    ssh_commands_executed INTEGER DEFAULT 0,
    cache_hit_ratio NUMERIC(5, 2),
    cache_size_entries INTEGER,
    cache_evictions INTEGER DEFAULT 0,
    data_collected_bytes BIGINT DEFAULT 0,
    database_writes INTEGER DEFAULT 0,
    error_types JSONB,
    top_errors JSONB,
    PRIMARY KEY (time, service_name)
);

-- 5. Cache Metadata Table
CREATE TABLE IF NOT EXISTS cache_metadata (
    cache_key VARCHAR(255) PRIMARY KEY,
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    data_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    access_count INTEGER DEFAULT 1,
    data_size_bytes INTEGER,
    ttl_seconds INTEGER NOT NULL,
    invalidated BOOLEAN DEFAULT FALSE,
    invalidated_at TIMESTAMPTZ,
    invalidation_reason VARCHAR(100),
    collection_method VARCHAR(50),
    command_hash VARCHAR(64)
);

-- Convert all time-series tables to TimescaleDB hypertables
SELECT create_hypertable('system_metrics', 'time', if_not_exists => TRUE);
SELECT create_hypertable('container_snapshots', 'time', if_not_exists => TRUE);
SELECT create_hypertable('drive_health', 'time', if_not_exists => TRUE);
SELECT create_hypertable('data_collection_audit', 'time', if_not_exists => TRUE);
SELECT create_hypertable('configuration_snapshots', 'time', if_not_exists => TRUE);
SELECT create_hypertable('configuration_change_events', 'time', if_not_exists => TRUE);
SELECT create_hypertable('service_performance_metrics', 'time', if_not_exists => TRUE);
```

### **Steps 2-11: Design and Implement SQLAlchemy Models**

**Objective**: Create the SQLAlchemy ORM models corresponding to the new database tables.
**Implementation**: Create the new Python files in `apps/backend/src/models/` and define the classes.

### **Step 12: Implement Fresh Database Migration Strategy**

**Objective**: Use Alembic to manage the new, unified schema.
**Implementation**: Generate a new, single Alembic revision.

1.  Run `alembic revision --autogenerate -m "Create unified infrastructure schema"`.
2.  Edit the generated script, set `revises = None`, and ensure the `upgrade()` function contains all `op.create_table()` calls. The `downgrade()` function can be `pass`.

### **Steps 13-18: Configure TimescaleDB and Monitoring**

**Objective**: Apply TimescaleDB-specific optimizations and set up monitoring.
**Implementation**:

1.  **Policies & Indexes**: Create `apps/backend/init-scripts/03-policies.sql` with `add_compression_policy`, `add_retention_policy`, and `CREATE INDEX` statements for all hypertables.
2.  **Health Monitoring**: Update the `check_database_health` function in `apps/backend/src/core/database.py` to include checks for the new tables, hypertable status, and job statistics.
3.  **Performance Queries**: Create `analysis_queries/performance.sql` with queries to analyze data collection performance, configuration changes, and service metrics.

---

## **Part 1.B: API Schema Definition (Pydantic Models)**

### **Step 19: Create New Schemas for New Models**

**Objective**: Define the Pydantic schemas that will serve as the data contracts for the new database models.
**Implementation**: Create four new files (`audit.py`, `configuration.py`, `performance.py`, `cache.py`) in the `apps/backend/src/schemas/` directory.

```python
# file: apps/backend/src/schemas/audit.py
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import List, Optional

class DataCollectionAudit(BaseModel):
    time: datetime
    device_id: UUID4
    operation_id: UUID4
    data_type: str
    collection_method: str
    status: str
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        orm_mode = True

class PaginatedAuditResponse(BaseModel):
    items: List[DataCollectionAudit]
    total: int
    page: int
    page_size: int
```

```python
# file: apps/backend/src/schemas/configuration.py
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import List, Optional, Dict, Any

class ConfigurationSnapshot(BaseModel):
    id: UUID4
    time: datetime
    config_type: str
    file_path: str
    content_hash: str
    risk_level: str

    class Config:
        orm_mode = True

class ConfigurationChangeEvent(BaseModel):
    id: UUID4
    time: datetime
    config_type: str
    file_path: str
    change_type: str
    risk_level: str

    class Config:
        orm_mode = True
```

```python
# file: apps/backend/src/schemas/performance.py
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import List, Optional

class ServicePerformanceMetric(BaseModel):
    time: datetime
    service_name: str
    avg_duration_ms: Optional[float] = None
    operations_total: int
    cache_hit_ratio: Optional[float] = None

    class Config:
        orm_mode = True
```

```python
# file: apps/backend/src/schemas/cache.py
from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional

class CacheMetadata(BaseModel):
    cache_key: str
    device_id: UUID4
    data_type: str
    created_at: datetime
    expires_at: datetime
    access_count: int

    class Config:
        orm_mode = True
```

### **Step 20: Refactor Existing Schemas**

**Objective**: Update existing Pydantic schemas to align with the unified data source and remove direct SSH-related fields.

**Implementation**:

1.  **`schemas/device.py`**:
    -   **Remove**: `ssh_port`, `ssh_username` from `DeviceBase` and `DeviceUpdate`. This data is now managed internally.
    -   **Add**: `last_successful_collection: Optional[datetime]` and `last_collection_status: Optional[str]` to `DeviceResponse`.
    -   **Deprecate**: `DeviceConnectionTest` will be replaced by a unified health check.

2.  **`schemas/container.py`**:
    -   **Refactor**: `ContainerSummary` and `ContainerDetails` will now be populated from the `ContainerSnapshot` database model.
    -   **Remove**: Any fields that imply a live SSH query. The API's primary source is now the database.

3.  **`schemas/system_metrics.py`**:
    -   **Align**: Ensure `SystemMetricResponse` and `SystemMetricsAggregated` perfectly map to the `SystemMetric` database model.

4.  **`schemas/proxy_config.py`**:
    -   **Integrate**: Refactor `ProxyConfigResponse` to link to the new `ConfigurationSnapshot` system via a `snapshot_id`.

### **Step 21: Implement Specific Response Models**

**Objective**: Create consistent and predictable API responses using specific Pydantic models.

**Implementation**: Define clear, minimal response models for various API operations to standardize outputs.

```python
# file: apps/backend/src/schemas/common.py (Additions)

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: Optional[str] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int
```

```python
# file: apps/backend/src/schemas/device.py (New addition)

class DeviceListResponse(PaginatedResponse[DeviceSummary]):
    """Specific response for listing devices."""
    pass

class DeviceDetailResponse(APIResponse[DeviceResponse]):
    """Specific response for getting a single device's details."""
    pass
```

### **Step 22: Add and Enhance Pydantic Validation**

**Objective**: Use Pydantic's validators to enforce data integrity and business rules at the API boundary.

**Implementation**: Add `@field_validator` decorators to the Pydantic models where necessary.

```python
# file: apps/backend/src/schemas/common.py (Enhancement)
from pydantic import field_validator

class TimeRangeParams(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @field_validator('end_time')
    def end_time_must_be_after_start_time(cls, v, info):
        if v and info.data.get('start_time') and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v