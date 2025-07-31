"""
Alembic Models - SQLAlchemy Models for Database Migration
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
import sqlalchemy as sa
from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime, Text, 
    ForeignKey, Numeric, Date, ARRAY, JSON
)
from sqlalchemy.dialects.postgresql import UUID, INET, MACADDR, CIDR, JSONB
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

# SQLAlchemy declarative base
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)

Base = declarative_base(metadata=metadata)


class Device(Base):
    """Device registry table for infrastructure nodes"""
    __tablename__ = "devices"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False)
    
    # Device identification
    hostname = Column(String(255), nullable=False, unique=True, index=True)
    ip_address = Column(INET, nullable=False, index=True)
    mac_address = Column(MACADDR, nullable=True)
    
    # Device classification
    device_type = Column(String(50), nullable=False, default="server")  # server, workstation, router, etc.
    operating_system = Column(String(100), nullable=True)
    architecture = Column(String(50), nullable=True)  # x86_64, arm64, etc.
    
    # Status and monitoring
    status = Column(String(20), nullable=False, default="unknown")  # online, offline, maintenance, unknown
    last_seen = Column(DateTime(timezone=True), nullable=True)
    
    # SSH connection info
    ssh_port = Column(Integer, nullable=False, default=22)
    ssh_user = Column(String(100), nullable=True)
    ssh_key_path = Column(Text, nullable=True)
    
    # Location and organization
    location = Column(String(255), nullable=True)
    environment = Column(String(50), nullable=True)  # production, staging, development
    tags = Column(ARRAY(String), nullable=True, default=list)
    
    # Metadata
    metadata_info = Column(JSONB, nullable=True, default=dict)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    system_metrics = relationship("SystemMetric", back_populates="device", cascade="all, delete-orphan")
    drive_health = relationship("DriveHealth", back_populates="device", cascade="all, delete-orphan")
    container_snapshots = relationship("ContainerSnapshot", back_populates="device", cascade="all, delete-orphan")
    zfs_status = relationship("ZFSStatus", back_populates="device", cascade="all, delete-orphan")
    zfs_snapshots = relationship("ZFSSnapshot", back_populates="device", cascade="all, delete-orphan")


class SystemMetric(Base):
    """Time-series system performance metrics (hypertable)"""
    __tablename__ = "system_metrics"
    
    # Composite primary key for hypertable
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    
    # CPU metrics
    cpu_usage_percent = Column(Numeric(5, 2), nullable=True)  # 0.00 to 100.00
    cpu_load_1min = Column(Numeric(8, 4), nullable=True)
    cpu_load_5min = Column(Numeric(8, 4), nullable=True)
    cpu_load_15min = Column(Numeric(8, 4), nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    cpu_temperature = Column(Numeric(5, 2), nullable=True)
    
    # Memory metrics (in bytes)
    memory_total_bytes = Column(BigInteger, nullable=True)
    memory_used_bytes = Column(BigInteger, nullable=True)
    memory_available_bytes = Column(BigInteger, nullable=True)
    memory_cached_bytes = Column(BigInteger, nullable=True)
    memory_buffers_bytes = Column(BigInteger, nullable=True)
    swap_total_bytes = Column(BigInteger, nullable=True)
    swap_used_bytes = Column(BigInteger, nullable=True)
    
    # Disk I/O metrics
    disk_read_bytes_total = Column(BigInteger, nullable=True)
    disk_write_bytes_total = Column(BigInteger, nullable=True)
    disk_read_ops_total = Column(BigInteger, nullable=True)
    disk_write_ops_total = Column(BigInteger, nullable=True)
    disk_usage_percent = Column(Numeric(5, 2), nullable=True)
    disk_available_bytes = Column(BigInteger, nullable=True)
    
    # Network I/O metrics
    network_bytes_sent_total = Column(BigInteger, nullable=True)
    network_bytes_recv_total = Column(BigInteger, nullable=True)
    network_packets_sent_total = Column(BigInteger, nullable=True)
    network_packets_recv_total = Column(BigInteger, nullable=True)
    network_errors_total = Column(BigInteger, nullable=True)
    
    # System uptime and processes
    uptime_seconds = Column(BigInteger, nullable=True)
    processes_total = Column(Integer, nullable=True)
    processes_running = Column(Integer, nullable=True)
    processes_sleeping = Column(Integer, nullable=True)
    processes_zombie = Column(Integer, nullable=True)
    
    # Additional system metrics
    boot_time = Column(DateTime(timezone=True), nullable=True)
    users_logged_in = Column(Integer, nullable=True)
    
    # Relationship
    device = relationship("Device", back_populates="system_metrics")


class DriveHealth(Base):
    """S.M.A.R.T. drive health monitoring data (hypertable)"""
    __tablename__ = "drive_health"
    
    # Composite primary key for hypertable
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    drive_name = Column(String(255), primary_key=True, nullable=False)  # /dev/sda, /dev/nvme0n1, etc.
    
    # Drive information
    drive_model = Column(String(255), nullable=True)
    drive_serial = Column(String(255), nullable=True)
    drive_type = Column(String(50), nullable=True)  # HDD, SSD, NVMe
    drive_size_bytes = Column(BigInteger, nullable=True)
    drive_firmware = Column(String(100), nullable=True)
    
    # S.M.A.R.T. status
    smart_status = Column(String(20), nullable=True)  # PASSED, FAILED, UNKNOWN
    smart_overall_health = Column(String(50), nullable=True)
    
    # Critical S.M.A.R.T. attributes
    temperature_celsius = Column(Integer, nullable=True)
    power_on_hours = Column(BigInteger, nullable=True)
    power_cycle_count = Column(BigInteger, nullable=True)
    reallocated_sectors = Column(Integer, nullable=True)
    reallocated_events = Column(Integer, nullable=True)
    current_pending_sectors = Column(Integer, nullable=True)
    offline_uncorrectable = Column(Integer, nullable=True)
    
    # SSD-specific attributes
    wear_leveling_count = Column(Integer, nullable=True)
    used_reserved_blocks = Column(Integer, nullable=True)
    program_fail_count = Column(Integer, nullable=True)
    erase_fail_count = Column(Integer, nullable=True)
    
    # Performance metrics
    read_error_rate = Column(BigInteger, nullable=True)
    seek_error_rate = Column(BigInteger, nullable=True)
    spin_retry_count = Column(Integer, nullable=True)
    
    # Additional health indicators
    airflow_temperature = Column(Integer, nullable=True)
    g_sense_error_rate = Column(Integer, nullable=True)
    head_flying_hours = Column(BigInteger, nullable=True)
    
    # Raw S.M.A.R.T. data
    smart_attributes = Column(JSONB, nullable=True, default=dict)
    
    # Relationship
    device = relationship("Device", back_populates="drive_health")


class ContainerSnapshot(Base):
    """Docker container runtime snapshots (hypertable)"""
    __tablename__ = "container_snapshots"
    
    # Composite primary key for hypertable
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    container_id = Column(String(64), primary_key=True, nullable=False)
    
    # Container identification
    container_name = Column(String(255), nullable=False)
    image = Column(String(255), nullable=True)
    image_id = Column(String(64), nullable=True)
    
    # Container status
    status = Column(String(50), nullable=True)  # running, exited, paused, etc.
    state = Column(String(50), nullable=True)
    running = Column(Boolean, nullable=True)
    paused = Column(Boolean, nullable=True)
    restarting = Column(Boolean, nullable=True)
    oom_killed = Column(Boolean, nullable=True)
    dead = Column(Boolean, nullable=True)
    pid = Column(Integer, nullable=True)
    exit_code = Column(Integer, nullable=True)
    
    # Resource usage
    cpu_usage_percent = Column(Numeric(5, 2), nullable=True)
    memory_usage_bytes = Column(BigInteger, nullable=True)
    memory_limit_bytes = Column(BigInteger, nullable=True)
    memory_cache_bytes = Column(BigInteger, nullable=True)
    
    # Network I/O
    network_bytes_sent = Column(BigInteger, nullable=True)
    network_bytes_recv = Column(BigInteger, nullable=True)
    
    # Block I/O
    block_read_bytes = Column(BigInteger, nullable=True)
    block_write_bytes = Column(BigInteger, nullable=True)
    
    # Container configuration
    ports = Column(JSONB, nullable=True, default=list)
    environment = Column(JSONB, nullable=True, default=dict)
    labels = Column(JSONB, nullable=True, default=dict)
    volumes = Column(JSONB, nullable=True, default=list)
    networks = Column(JSONB, nullable=True, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    device = relationship("Device", back_populates="container_snapshots")


class ZFSStatus(Base):
    """ZFS pool and dataset status monitoring (hypertable)"""
    __tablename__ = "zfs_status"
    
    # Composite primary key for hypertable
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    pool_name = Column(String(255), primary_key=True, nullable=False)
    
    # Pool status
    pool_state = Column(String(50), nullable=True)  # ONLINE, DEGRADED, FAULTED, OFFLINE
    pool_health = Column(String(50), nullable=True)
    pool_guid = Column(String(100), nullable=True)
    
    # Pool capacity
    pool_size_bytes = Column(BigInteger, nullable=True)
    pool_allocated_bytes = Column(BigInteger, nullable=True)
    pool_free_bytes = Column(BigInteger, nullable=True)
    pool_fragmentation_percent = Column(Numeric(5, 2), nullable=True)
    pool_capacity_percent = Column(Numeric(5, 2), nullable=True)
    
    # Pool performance
    read_ops_total = Column(BigInteger, nullable=True)
    write_ops_total = Column(BigInteger, nullable=True)
    read_bytes_total = Column(BigInteger, nullable=True)
    write_bytes_total = Column(BigInteger, nullable=True)
    
    # Scrub information
    scrub_state = Column(String(50), nullable=True)  # none, scanning, finished, canceled
    scrub_start_time = Column(DateTime(timezone=True), nullable=True)
    scrub_end_time = Column(DateTime(timezone=True), nullable=True)
    scrub_examined_bytes = Column(BigInteger, nullable=True)
    scrub_processed_bytes = Column(BigInteger, nullable=True)
    scrub_errors = Column(Integer, nullable=True)
    scrub_repaired_bytes = Column(BigInteger, nullable=True)
    
    # Pool errors
    read_errors = Column(Integer, nullable=True)
    write_errors = Column(Integer, nullable=True)
    checksum_errors = Column(Integer, nullable=True)
    
    # Pool configuration and properties
    pool_version = Column(Integer, nullable=True)
    feature_flags = Column(JSONB, nullable=True, default=dict)
    pool_properties = Column(JSONB, nullable=True, default=dict)
    
    # Dataset information (if this row represents a dataset)
    dataset_name = Column(String(255), nullable=True)
    dataset_type = Column(String(50), nullable=True)  # filesystem, volume, snapshot
    dataset_used_bytes = Column(BigInteger, nullable=True)
    dataset_available_bytes = Column(BigInteger, nullable=True)
    dataset_referenced_bytes = Column(BigInteger, nullable=True)
    dataset_compression_ratio = Column(Numeric(8, 4), nullable=True)
    dataset_properties = Column(JSONB, nullable=True, default=dict)
    
    # Relationship
    device = relationship("Device", back_populates="zfs_status")


class ZFSSnapshot(Base):
    """ZFS snapshot tracking and management (hypertable)"""
    __tablename__ = "zfs_snapshots"
    
    # Composite primary key for hypertable
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    snapshot_name = Column(String(255), primary_key=True, nullable=False)
    
    # Snapshot identification
    pool_name = Column(String(255), nullable=False)
    dataset_name = Column(String(255), nullable=False)
    snapshot_guid = Column(String(100), nullable=True)
    
    # Snapshot metadata
    creation_time = Column(DateTime(timezone=True), nullable=True)
    used_bytes = Column(BigInteger, nullable=True)
    referenced_bytes = Column(BigInteger, nullable=True)
    compressed_bytes = Column(BigInteger, nullable=True)
    uncompressed_bytes = Column(BigInteger, nullable=True)
    
    # Snapshot properties
    snapshot_type = Column(String(50), nullable=True)  # manual, automatic, backup
    retention_policy = Column(String(100), nullable=True)
    snapshot_properties = Column(JSONB, nullable=True, default=dict)
    
    # Backup and replication status
    backup_status = Column(String(50), nullable=True)  # pending, completed, failed
    replication_status = Column(String(50), nullable=True)
    last_backup_time = Column(DateTime(timezone=True), nullable=True)
    backup_destination = Column(String(255), nullable=True)
    
    # Snapshot lifecycle
    is_cloned = Column(Boolean, nullable=True, default=False)
    clone_count = Column(Integer, nullable=True, default=0)
    is_held = Column(Boolean, nullable=True, default=False)
    hold_tag = Column(String(255), nullable=True)
    
    # Relationship
    device = relationship("Device", back_populates="zfs_snapshots")


class NetworkInterface(Base):
    """Network interface monitoring data (hypertable)"""
    __tablename__ = "network_interfaces"
    
    # Composite primary key for hypertable
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    interface_name = Column(String(255), primary_key=True, nullable=False)
    
    # Interface properties
    interface_type = Column(String(50), nullable=True)  # ethernet, wifi, bridge, etc.
    mtu = Column(Integer, nullable=True)
    speed_mbps = Column(Integer, nullable=True)
    duplex = Column(String(20), nullable=True)  # full, half
    
    # Interface status
    is_up = Column(Boolean, nullable=True)
    is_running = Column(Boolean, nullable=True)
    carrier_state = Column(String(20), nullable=True)
    
    # Network addresses
    ip_addresses = Column(JSONB, nullable=True, default=list)
    mac_address = Column(MACADDR, nullable=True)
    
    # Traffic statistics
    bytes_sent = Column(BigInteger, nullable=True)
    bytes_recv = Column(BigInteger, nullable=True)
    packets_sent = Column(BigInteger, nullable=True)
    packets_recv = Column(BigInteger, nullable=True)
    errors_sent = Column(BigInteger, nullable=True)
    errors_recv = Column(BigInteger, nullable=True)
    drops_sent = Column(BigInteger, nullable=True)
    drops_recv = Column(BigInteger, nullable=True)
    collisions = Column(BigInteger, nullable=True)
    
    # Wireless-specific (if applicable)
    wireless_ssid = Column(String(255), nullable=True)
    wireless_signal_strength = Column(Integer, nullable=True)
    wireless_frequency = Column(Numeric(8, 3), nullable=True)
    
    # VLAN information
    vlan_id = Column(Integer, nullable=True)
    vlan_priority = Column(Integer, nullable=True)
    
    # Bridge information
    bridge_id = Column(String(100), nullable=True)
    bridge_stp_state = Column(String(20), nullable=True)


class DockerNetwork(Base):
    """Docker network topology monitoring (hypertable)"""
    __tablename__ = "docker_networks"
    
    # Composite primary key for hypertable  
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    network_id = Column(String(64), primary_key=True, nullable=False)
    
    # Network identification
    network_name = Column(String(255), nullable=False)
    driver = Column(String(100), nullable=True)
    scope = Column(String(50), nullable=True)  # local, global, swarm
    
    # Network configuration
    subnet = Column(CIDR, nullable=True)
    gateway = Column(INET, nullable=True)
    ip_range = Column(CIDR, nullable=True)
    
    # Network state
    is_internal = Column(Boolean, nullable=True)
    enable_ipv6 = Column(Boolean, nullable=True)
    attachable = Column(Boolean, nullable=True)
    ingress = Column(Boolean, nullable=True)
    
    # Connected containers
    connected_containers = Column(JSONB, nullable=True, default=list)
    container_count = Column(Integer, nullable=True, default=0)
    
    # Network options and labels
    driver_options = Column(JSONB, nullable=True, default=dict)
    labels = Column(JSONB, nullable=True, default=dict)
    
    # Network creation info
    created_at = Column(DateTime(timezone=True), nullable=True)


class VMStatus(Base):
    """Virtual machine status monitoring (hypertable)"""
    __tablename__ = "vm_status"
    
    # Composite primary key for hypertable
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    vm_id = Column(String(255), primary_key=True, nullable=False)
    
    # VM identification
    vm_name = Column(String(255), nullable=False)
    vm_type = Column(String(50), nullable=True)  # kvm, vmware, virtualbox, etc.
    hypervisor = Column(String(100), nullable=True)
    
    # VM state
    vm_state = Column(String(50), nullable=True)  # running, stopped, paused, suspended
    vm_power_state = Column(String(50), nullable=True)
    
    # Resource allocation
    cpu_cores = Column(Integer, nullable=True)
    memory_allocated_mb = Column(BigInteger, nullable=True)
    disk_allocated_gb = Column(BigInteger, nullable=True)
    
    # Resource usage
    cpu_usage_percent = Column(Numeric(5, 2), nullable=True)
    memory_usage_mb = Column(BigInteger, nullable=True)
    disk_usage_gb = Column(BigInteger, nullable=True)
    
    # Network information
    network_interfaces = Column(JSONB, nullable=True, default=list)
    ip_addresses = Column(JSONB, nullable=True, default=list)
    
    # VM configuration
    os_type = Column(String(100), nullable=True)
    os_version = Column(String(100), nullable=True)
    tools_version = Column(String(100), nullable=True)
    tools_running = Column(Boolean, nullable=True)
    
    # VM lifecycle
    created_at = Column(DateTime(timezone=True), nullable=True)
    boot_time = Column(DateTime(timezone=True), nullable=True)
    uptime_seconds = Column(BigInteger, nullable=True)
    
    # Snapshot information
    snapshot_count = Column(Integer, nullable=True, default=0)
    last_snapshot_time = Column(DateTime(timezone=True), nullable=True)
    
    # VM metadata
    vm_metadata = Column(JSONB, nullable=True, default=dict)
    tags = Column(ARRAY(String), nullable=True, default=list)


class SystemLog(Base):
    """System log analysis and monitoring (hypertable)"""
    __tablename__ = "system_logs"
    
    # Composite primary key for hypertable
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    log_id = Column(String(64), primary_key=True, nullable=False)  # Hash of log entry
    
    # Log source
    log_source = Column(String(255), nullable=True)  # /var/log/syslog, journald, etc.
    service_name = Column(String(255), nullable=True)
    facility = Column(String(50), nullable=True)
    
    # Log severity and classification
    severity = Column(String(20), nullable=True)  # emergency, alert, critical, error, warning, notice, info, debug
    log_level = Column(String(20), nullable=True)
    priority = Column(Integer, nullable=True)
    
    # Log content
    message = Column(Text, nullable=False)
    raw_message = Column(Text, nullable=True)
    hostname = Column(String(255), nullable=True)
    
    # Log parsing and analysis
    parsed_fields = Column(JSONB, nullable=True, default=dict)
    event_type = Column(String(100), nullable=True)
    event_category = Column(String(100), nullable=True)
    
    # Log aggregation and counting
    occurrence_count = Column(Integer, nullable=True, default=1)
    first_occurrence = Column(DateTime(timezone=True), nullable=True)
    last_occurrence = Column(DateTime(timezone=True), nullable=True)
    
    # Log correlation
    correlation_id = Column(String(64), nullable=True)
    thread_id = Column(String(64), nullable=True)
    process_id = Column(Integer, nullable=True)
    user_id = Column(String(255), nullable=True)
    
    # Security and alerting
    is_security_event = Column(Boolean, nullable=True, default=False)
    is_error = Column(Boolean, nullable=True, default=False)
    alert_triggered = Column(Boolean, nullable=True, default=False)
    alert_rule = Column(String(255), nullable=True)
    
    # Log metadata
    log_metadata = Column(JSONB, nullable=True, default=dict)
    tags = Column(ARRAY(String), nullable=True, default=list)


class BackupStatus(Base):
    """Backup monitoring and verification (hypertable)"""
    __tablename__ = "backup_status"
    
    # Composite primary key for hypertable
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    backup_id = Column(String(255), primary_key=True, nullable=False)
    
    # Backup identification
    backup_name = Column(String(255), nullable=False)
    backup_type = Column(String(50), nullable=True)  # full, incremental, differential, snapshot
    backup_method = Column(String(100), nullable=True)  # rsync, zfs, tar, borg, etc.
    
    # Backup source and destination
    source_path = Column(Text, nullable=True)
    destination_path = Column(Text, nullable=True)
    backup_location = Column(String(255), nullable=True)  # local, remote, cloud
    
    # Backup execution
    backup_start_time = Column(DateTime(timezone=True), nullable=True)
    backup_end_time = Column(DateTime(timezone=True), nullable=True)
    backup_duration_seconds = Column(Integer, nullable=True)
    backup_status = Column(String(50), nullable=True)  # pending, running, completed, failed, partial
    
    # Backup size and performance
    data_size_bytes = Column(BigInteger, nullable=True)
    backup_size_bytes = Column(BigInteger, nullable=True)
    compression_ratio = Column(Numeric(5, 4), nullable=True)
    deduplication_ratio = Column(Numeric(5, 4), nullable=True)
    transfer_rate_mbps = Column(Numeric(10, 2), nullable=True)
    
    # Backup verification
    verification_status = Column(String(50), nullable=True)  # pending, passed, failed, skipped
    verification_method = Column(String(100), nullable=True)
    checksum = Column(String(255), nullable=True)
    checksum_algorithm = Column(String(50), nullable=True)
    
    # Error handling
    error_count = Column(Integer, nullable=True, default=0)
    warning_count = Column(Integer, nullable=True, default=0)
    error_messages = Column(JSONB, nullable=True, default=list)
    
    # Retention and lifecycle
    retention_days = Column(Integer, nullable=True)
    expiry_date = Column(Date, nullable=True)
    is_archived = Column(Boolean, nullable=True, default=False)
    archive_location = Column(String(255), nullable=True)
    
    # Backup metadata
    backup_metadata = Column(JSONB, nullable=True, default=dict)
    backup_config = Column(JSONB, nullable=True, default=dict)
    tags = Column(ARRAY(String), nullable=True, default=list)


class SystemUpdate(Base):
    """System update and patch management (hypertable)"""
    __tablename__ = "system_updates"
    
    # Composite primary key for hypertable
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    device_id = Column(UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True, nullable=False)
    update_id = Column(String(255), primary_key=True, nullable=False)
    
    # Update identification
    package_name = Column(String(255), nullable=False)
    package_type = Column(String(50), nullable=True)  # apt, yum, dnf, pacman, docker, etc.
    current_version = Column(String(255), nullable=True)
    available_version = Column(String(255), nullable=True)
    
    # Update classification
    update_type = Column(String(50), nullable=True)  # security, critical, important, moderate, low
    severity = Column(String(20), nullable=True)
    category = Column(String(100), nullable=True)
    
    # Update status
    update_status = Column(String(50), nullable=True)  # available, downloading, installing, installed, failed
    is_security_update = Column(Boolean, nullable=True, default=False)
    requires_reboot = Column(Boolean, nullable=True, default=False)
    is_auto_update = Column(Boolean, nullable=True, default=False)
    
    # Update timing
    release_date = Column(Date, nullable=True)
    install_date = Column(DateTime(timezone=True), nullable=True)
    install_duration_seconds = Column(Integer, nullable=True)
    
    # Update size and dependencies
    download_size_bytes = Column(BigInteger, nullable=True)
    install_size_bytes = Column(BigInteger, nullable=True)
    dependencies = Column(JSONB, nullable=True, default=list)
    
    # Repository information
    repository = Column(String(255), nullable=True)
    repository_url = Column(String(255), nullable=True)
    maintainer = Column(String(255), nullable=True)
    
    # Update description and changelog
    description = Column(Text, nullable=True)
    changelog = Column(Text, nullable=True)
    cve_numbers = Column(ARRAY(String), nullable=True, default=list)
    
    # Update verification
    signature_valid = Column(Boolean, nullable=True)
    checksum = Column(String(255), nullable=True)
    checksum_algorithm = Column(String(50), nullable=True)
    
    # Error handling
    error_code = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=True, default=0)
    
    # Update metadata
    update_metadata = Column(JSONB, nullable=True, default=dict)
    tags = Column(ARRAY(String), nullable=True, default=list)