"""
ZFS Management API Endpoints

REST API endpoints for ZFS pool management, dataset operations, snapshot handling,
health monitoring, and performance analysis via SSH commands.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Any
from pydantic import BaseModel, Field

from apps.backend.src.api.common import get_current_user
from apps.backend.src.core.exceptions import SSHConnectionError, ZFSError
from apps.backend.src.services.zfs import (
    ZFSAnalysisService,
    ZFSDatasetService,
    ZFSHealthService,
    ZFSPoolService,
    ZFSSnapshotService,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def get_pool_service() -> ZFSPoolService:
    return ZFSPoolService()


def get_dataset_service() -> ZFSDatasetService:
    return ZFSDatasetService()


def get_snapshot_service() -> ZFSSnapshotService:
    return ZFSSnapshotService()


def get_health_service() -> ZFSHealthService:
    return ZFSHealthService()


def get_analysis_service() -> ZFSAnalysisService:
    return ZFSAnalysisService()


# Request/Response Models
class SnapshotCreateRequest(BaseModel):
    dataset_name: str = Field(..., description="Dataset name to snapshot")
    snapshot_name: str = Field(..., description="Snapshot name")
    recursive: bool = Field(default=False, description="Create recursive snapshot")


class SnapshotCloneRequest(BaseModel):
    clone_name: str = Field(..., description="Name for the cloned dataset")


class SnapshotSendRequest(BaseModel):
    destination: str | None = Field(None, description="Destination for snapshot send")
    incremental: bool = Field(default=False, description="Use incremental send")


class SnapshotReceiveRequest(BaseModel):
    dataset_name: str = Field(..., description="Dataset name for receiving snapshot")


class SnapshotDiffRequest(BaseModel):
    snapshot2: str = Field(..., description="Second snapshot for comparison")


# Pool Management Endpoints
@router.get("/{hostname}/pools")
async def list_zfs_pools(
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    service: ZFSPoolService = Depends(get_pool_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """List all ZFS pools on a device"""
    try:
        pools = await service.list_pools(hostname, timeout)
        return {"hostname": hostname, "pools": pools, "total_pools": len(pools)}
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error listing ZFS pools on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list ZFS pools") from e


@router.get("/{hostname}/pools/{pool_name}/status")
async def get_pool_status(
    hostname: str = Path(..., description="Device hostname"),
    pool_name: str = Path(..., description="ZFS pool name"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    service: ZFSPoolService = Depends(get_pool_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get detailed status for a specific ZFS pool"""
    try:
        status = await service.get_pool_status(hostname, pool_name, timeout)
        return status
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting pool status for {pool_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get pool status") from e


# Dataset Management Endpoints
@router.get("/{hostname}/datasets")
async def list_zfs_datasets(
    hostname: str = Path(..., description="Device hostname"),
    pool_name: str | None = Query(None, description="Filter by pool name"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    service: ZFSDatasetService = Depends(get_dataset_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """List ZFS datasets, optionally filtered by pool"""
    try:
        datasets = await service.list_datasets(hostname, pool_name, timeout)
        return {
            "hostname": hostname,
            "pool_name": pool_name,
            "datasets": datasets,
            "total_datasets": len(datasets),
        }
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error listing ZFS datasets on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list ZFS datasets") from e


@router.get("/{hostname}/datasets/{dataset_name}/properties")
async def get_dataset_properties(
    hostname: str = Path(..., description="Device hostname"),
    dataset_name: str = Path(..., description="Dataset name"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    service: ZFSDatasetService = Depends(get_dataset_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get all properties for a specific dataset"""
    try:
        properties = await service.get_dataset_properties(hostname, dataset_name, timeout)
        return properties
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting dataset properties for {dataset_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dataset properties") from e


# Snapshot Management Endpoints
@router.get("/{hostname}/snapshots")
async def list_zfs_snapshots(
    hostname: str = Path(..., description="Device hostname"),
    dataset_name: str | None = Query(None, description="Filter by dataset name"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    service: ZFSSnapshotService = Depends(get_snapshot_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """List ZFS snapshots, optionally filtered by dataset"""
    try:
        snapshots = await service.list_snapshots(hostname, dataset_name, timeout)
        return {
            "hostname": hostname,
            "dataset_name": dataset_name,
            "snapshots": snapshots,
            "total_snapshots": len(snapshots),
        }
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error listing ZFS snapshots on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to list ZFS snapshots") from e


@router.post("/{hostname}/snapshots")
async def create_zfs_snapshot(
    request: SnapshotCreateRequest,
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    service: ZFSSnapshotService = Depends(get_snapshot_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new ZFS snapshot"""
    try:
        result = await service.create_snapshot(
            hostname, request.dataset_name, request.snapshot_name, request.recursive, timeout
        )
        return result
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error creating snapshot {request.snapshot_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create snapshot") from e


@router.post("/{hostname}/snapshots/{snapshot_name}/clone")
async def clone_zfs_snapshot(
    request: SnapshotCloneRequest,
    hostname: str = Path(..., description="Device hostname"),
    snapshot_name: str = Path(..., description="Snapshot name to clone"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    service: ZFSSnapshotService = Depends(get_snapshot_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Clone a ZFS snapshot"""
    try:
        result = await service.clone_snapshot(hostname, snapshot_name, request.clone_name, timeout)
        return result
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error cloning snapshot {snapshot_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to clone snapshot") from e


@router.post("/{hostname}/snapshots/{snapshot_name}/send")
async def send_zfs_snapshot(
    request: SnapshotSendRequest,
    hostname: str = Path(..., description="Device hostname"),
    snapshot_name: str = Path(..., description="Snapshot name to send"),
    timeout: int = Query(300, description="SSH timeout in seconds"),
    service: ZFSSnapshotService = Depends(get_snapshot_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Send a ZFS snapshot for replication/backup"""
    try:
        result = await service.send_snapshot(
            hostname, snapshot_name, request.destination, request.incremental, timeout
        )
        return result
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error sending snapshot {snapshot_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send snapshot") from e


@router.post("/{hostname}/receive")
async def receive_zfs_snapshot(
    request: SnapshotReceiveRequest,
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(300, description="SSH timeout in seconds"),
    service: ZFSSnapshotService = Depends(get_snapshot_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Receive a ZFS snapshot stream"""
    try:
        result = await service.receive_snapshot(hostname, request.dataset_name, timeout)
        return result
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error receiving snapshot for {request.dataset_name} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to receive snapshot") from e


@router.get("/{hostname}/snapshots/{snapshot_name}/diff")
async def diff_zfs_snapshots(
    hostname: str = Path(..., description="Device hostname"),
    snapshot_name: str = Path(..., description="First snapshot name"),
    snapshot2: str = Query(..., description="Second snapshot name for comparison"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    service: ZFSSnapshotService = Depends(get_snapshot_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Compare differences between two snapshots"""
    try:
        result = await service.diff_snapshots(hostname, snapshot_name, snapshot2, timeout)
        return result
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error diffing snapshots {snapshot_name} and {snapshot2} on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to diff snapshots") from e


# Health and Monitoring Endpoints
@router.get("/{hostname}/health")
async def check_zfs_health(
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    service: ZFSHealthService = Depends(get_health_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Comprehensive ZFS health check"""
    try:
        health = await service.check_zfs_health(hostname, timeout)
        return health
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error checking ZFS health on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check ZFS health") from e


@router.get("/{hostname}/arc-stats")
async def get_zfs_arc_stats(
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    service: ZFSHealthService = Depends(get_health_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get ZFS ARC (Adaptive Replacement Cache) statistics"""
    try:
        arc_stats = await service.get_arc_stats(hostname, timeout)
        return arc_stats
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error getting ARC stats on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get ARC stats") from e


@router.get("/{hostname}/events")
async def monitor_zfs_events(
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(30, description="SSH timeout in seconds"),
    service: ZFSHealthService = Depends(get_health_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Monitor ZFS events and error messages"""
    try:
        events = await service.monitor_zfs_events(hostname, timeout)
        return events
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error monitoring ZFS events on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to monitor ZFS events") from e


# Analysis and Reporting Endpoints
@router.get("/{hostname}/report")
async def generate_zfs_report(
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(120, description="SSH timeout in seconds"),
    service: ZFSAnalysisService = Depends(get_analysis_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate comprehensive ZFS report"""
    try:
        report = await service.generate_zfs_report(hostname, timeout)
        return report
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error generating ZFS report on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate ZFS report") from e


@router.get("/{hostname}/snapshots/usage")
async def analyze_snapshot_usage(
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    service: ZFSAnalysisService = Depends(get_analysis_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Analyze snapshot space usage and provide cleanup recommendations"""
    try:
        analysis = await service.analyze_snapshot_usage(hostname, timeout)
        return analysis
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error analyzing snapshot usage on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze snapshot usage") from e


@router.get("/{hostname}/optimize")
async def optimize_zfs_settings(
    hostname: str = Path(..., description="Device hostname"),
    timeout: int = Query(60, description="SSH timeout in seconds"),
    service: ZFSAnalysisService = Depends(get_analysis_service),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Analyze ZFS configuration and suggest optimizations"""
    try:
        optimization = await service.optimize_zfs_settings(hostname, timeout)
        return optimization
    except ZFSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except SSHConnectionError as e:
        raise HTTPException(status_code=503, detail=f"SSH connection failed: {str(e)}") from e
    except Exception as e:
        logger.error(f"Error optimizing ZFS settings on {hostname}: {e}")
        raise HTTPException(status_code=500, detail="Failed to optimize ZFS settings") from e
