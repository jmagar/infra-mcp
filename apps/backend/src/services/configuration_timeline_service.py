"""
Configuration Timeline Service

Provides comprehensive timeline visualization and diff analysis for configuration changes.
Tracks configuration evolution over time with detailed change visualization and impact analysis.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    BusinessLogicError,
)
from ..models.device import Device
from ..models.configuration import ConfigurationSnapshot, ConfigurationChangeEvent
from ..utils.diff_generator import DiffGenerator

logger = structlog.get_logger(__name__)


class ConfigurationTimelineService:
    """
    Service for generating configuration timeline and diff visualization data.

    Provides rich timeline data for understanding configuration evolution,
    change impacts, and historical context for configuration management.
    """

    def __init__(self):
        self.diff_generator = DiffGenerator()

    async def get_device_configuration_timeline(
        self,
        session: AsyncSession,
        device_id: UUID,
        file_path: str | None = None,
        days_back: int = 30,
        include_content: bool = False,
        include_diffs: bool = True,
    ) -> dict[str, Any]:
        """
        Get configuration timeline for a specific device.

        Args:
            session: Database session
            device_id: Device to get timeline for
            file_path: Optional specific file path filter
            days_back: Number of days of history to include
            include_content: Whether to include full file content
            include_diffs: Whether to include diff calculations

        Returns:
            Timeline data with events, changes, and visualizations
        """
        try:
            structlog.contextvars.bind_contextvars(
                operation="get_device_timeline",
                device_id=str(device_id),
                file_path=file_path,
                days_back=days_back,
            )

            logger.info("Getting configuration timeline for device")

            # Get device info
            device = await session.get(Device, device_id)
            if not device:
                raise ResourceNotFoundError(f"Device not found: {device_id}")

            # Calculate time range
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_back)

            # Build base query for change events
            events_query = (
                select(ConfigurationChangeEvent)
                .where(
                    and_(
                        ConfigurationChangeEvent.device_id == device_id,
                        ConfigurationChangeEvent.timestamp >= cutoff_time,
                    )
                )
                .options(selectinload(ConfigurationChangeEvent.snapshot))
                .order_by(desc(ConfigurationChangeEvent.timestamp))
            )

            # Add file path filter if specified
            if file_path:
                events_query = events_query.where(ConfigurationChangeEvent.file_path == file_path)

            # Execute query
            result = await session.execute(events_query)
            events = list(result.scalars().all())

            logger.info(f"Found {len(events)} configuration events")

            # Get snapshots for timeline
            snapshots_query = (
                select(ConfigurationSnapshot)
                .where(
                    and_(
                        ConfigurationSnapshot.device_id == device_id,
                        ConfigurationSnapshot.created_at >= cutoff_time,
                    )
                )
                .order_by(desc(ConfigurationSnapshot.created_at))
            )

            if file_path:
                snapshots_query = snapshots_query.where(
                    ConfigurationSnapshot.file_path == file_path
                )

            result = await session.execute(snapshots_query)
            snapshots = list(result.scalars().all())

            # Build timeline data
            timeline_data = await self._build_timeline_data(
                device=device,
                events=events,
                snapshots=snapshots,
                include_content=include_content,
                include_diffs=include_diffs,
                file_path=file_path,
            )

            return timeline_data

        except Exception as e:
            logger.error("Error getting device configuration timeline", error=str(e))
            raise

    async def get_configuration_file_history(
        self,
        session: AsyncSession,
        device_id: UUID,
        file_path: str,
        limit: int = 50,
        include_content: bool = True,
    ) -> dict[str, Any]:
        """
        Get detailed history for a specific configuration file.

        Args:
            session: Database session
            device_id: Device ID
            file_path: Specific file path
            limit: Maximum number of versions to return
            include_content: Whether to include full content

        Returns:
            Detailed file history with versions and diffs
        """
        try:
            structlog.contextvars.bind_contextvars(
                operation="get_file_history",
                device_id=str(device_id),
                file_path=file_path,
                limit=limit,
            )

            logger.info("Getting configuration file history")

            # Get device
            device = await session.get(Device, device_id)
            if not device:
                raise ResourceNotFoundError(f"Device not found: {device_id}")

            # Get snapshots for this file
            query = (
                select(ConfigurationSnapshot)
                .where(
                    and_(
                        ConfigurationSnapshot.device_id == device_id,
                        ConfigurationSnapshot.file_path == file_path,
                    )
                )
                .order_by(desc(ConfigurationSnapshot.created_at))
                .limit(limit)
            )

            result = await session.execute(query)
            snapshots = list(result.scalars().all())

            if not snapshots:
                return {
                    "device_id": str(device_id),
                    "device_name": device.hostname,
                    "file_path": file_path,
                    "versions": [],
                    "total_versions": 0,
                    "first_seen": None,
                    "last_modified": None,
                }

            # Build version history
            versions = []
            for i, snapshot in enumerate(snapshots):
                version_data = {
                    "version_id": str(snapshot.id),
                    "timestamp": snapshot.created_at.isoformat(),
                    "change_type": snapshot.change_type,
                    "content_hash": snapshot.content_hash,
                    "file_size": snapshot.file_size,
                    "metadata": snapshot.metadata,
                }

                if include_content and snapshot.content:
                    version_data["content"] = snapshot.content

                # Calculate diff with previous version
                if i < len(snapshots) - 1 and snapshot.content and snapshots[i + 1].content:
                    diff = self.diff_generator.generate_unified_diff(
                        old_content=snapshots[i + 1].content,
                        new_content=snapshot.content,
                        old_name=f"{file_path} (v{len(snapshots) - i})",
                        new_name=f"{file_path} (v{len(snapshots) - i - 1})",
                    )
                    version_data["diff"] = diff
                    version_data["changes_summary"] = self.diff_generator.get_diff_summary(diff)

                versions.append(version_data)

            # Get related change events
            events_query = (
                select(ConfigurationChangeEvent)
                .where(
                    and_(
                        ConfigurationChangeEvent.device_id == device_id,
                        ConfigurationChangeEvent.file_path == file_path,
                    )
                )
                .order_by(desc(ConfigurationChangeEvent.timestamp))
                .limit(limit)
            )

            result = await session.execute(events_query)
            events = list(result.scalars().all())

            return {
                "device_id": str(device_id),
                "device_name": device.hostname,
                "file_path": file_path,
                "versions": versions,
                "total_versions": len(snapshots),
                "first_seen": snapshots[-1].created_at.isoformat() if snapshots else None,
                "last_modified": snapshots[0].created_at.isoformat() if snapshots else None,
                "related_events": [
                    {
                        "event_id": str(event.id),
                        "timestamp": event.timestamp.isoformat(),
                        "change_type": event.change_type,
                        "risk_level": event.risk_level,
                        "triggered_by": event.triggered_by,
                        "impact_summary": event.impact_summary,
                    }
                    for event in events
                ],
                "file_stats": {
                    "avg_size": sum(s.file_size for s in snapshots if s.file_size) / len(snapshots)
                    if snapshots
                    else 0,
                    "min_size": min(s.file_size for s in snapshots if s.file_size)
                    if snapshots
                    else 0,
                    "max_size": max(s.file_size for s in snapshots if s.file_size)
                    if snapshots
                    else 0,
                    "change_frequency": len(events),
                },
            }

        except Exception as e:
            logger.error("Error getting configuration file history", error=str(e))
            raise

    async def compare_configuration_versions(
        self,
        session: AsyncSession,
        snapshot_id_1: UUID,
        snapshot_id_2: UUID,
        diff_format: str = "unified",
    ) -> dict[str, Any]:
        """
        Compare two configuration snapshots and generate diff visualization.

        Args:
            session: Database session
            snapshot_id_1: First snapshot ID (older)
            snapshot_id_2: Second snapshot ID (newer)
            diff_format: Diff format ('unified', 'side-by-side', 'json')

        Returns:
            Detailed comparison with diff visualization
        """
        try:
            structlog.contextvars.bind_contextvars(
                operation="compare_versions",
                snapshot_1=str(snapshot_id_1),
                snapshot_2=str(snapshot_id_2),
                diff_format=diff_format,
            )

            logger.info("Comparing configuration versions")

            # Get both snapshots
            snapshot1 = await session.get(ConfigurationSnapshot, snapshot_id_1)
            snapshot2 = await session.get(ConfigurationSnapshot, snapshot_id_2)

            if not snapshot1:
                raise ResourceNotFoundError(f"Snapshot not found: {snapshot_id_1}")
            if not snapshot2:
                raise ResourceNotFoundError(f"Snapshot not found: {snapshot_id_2}")

            # Ensure they're for the same file
            if (
                snapshot1.device_id != snapshot2.device_id
                or snapshot1.file_path != snapshot2.file_path
            ):
                raise ValidationError("Snapshots must be for the same device and file")

            # Generate diff based on format
            if diff_format == "unified":
                diff_content = self.diff_generator.generate_unified_diff(
                    old_content=snapshot1.content or "",
                    new_content=snapshot2.content or "",
                    old_name=f"{snapshot1.file_path} ({snapshot1.created_at.isoformat()})",
                    new_name=f"{snapshot2.file_path} ({snapshot2.created_at.isoformat()})",
                )
            elif diff_format == "side-by-side":
                diff_content = self.diff_generator.generate_side_by_side_diff(
                    old_content=snapshot1.content or "",
                    new_content=snapshot2.content or "",
                )
            elif diff_format == "json":
                diff_content = self.diff_generator.generate_json_diff(
                    old_content=snapshot1.content or "",
                    new_content=snapshot2.content or "",
                )
            else:
                raise ValidationError(f"Unsupported diff format: {diff_format}")

            # Calculate diff statistics
            diff_stats = self.diff_generator.get_diff_summary(diff_content)

            return {
                "comparison_id": f"{snapshot_id_1}-{snapshot_id_2}",
                "snapshot1": {
                    "id": str(snapshot1.id),
                    "timestamp": snapshot1.created_at.isoformat(),
                    "content_hash": snapshot1.content_hash,
                    "file_size": snapshot1.file_size,
                    "change_type": snapshot1.change_type,
                },
                "snapshot2": {
                    "id": str(snapshot2.id),
                    "timestamp": snapshot2.created_at.isoformat(),
                    "content_hash": snapshot2.content_hash,
                    "file_size": snapshot2.file_size,
                    "change_type": snapshot2.change_type,
                },
                "file_info": {
                    "device_id": str(snapshot1.device_id),
                    "file_path": snapshot1.file_path,
                },
                "diff": {
                    "format": diff_format,
                    "content": diff_content,
                    "statistics": diff_stats,
                    "time_delta": (snapshot2.created_at - snapshot1.created_at).total_seconds(),
                },
                "analysis": {
                    "content_changed": snapshot1.content_hash != snapshot2.content_hash,
                    "size_change": (snapshot2.file_size or 0) - (snapshot1.file_size or 0),
                    "risk_assessment": self._assess_change_risk(snapshot1, snapshot2, diff_stats),
                },
            }

        except Exception as e:
            logger.error("Error comparing configuration versions", error=str(e))
            raise

    async def get_configuration_change_impact(
        self,
        session: AsyncSession,
        change_event_id: UUID,
    ) -> dict[str, Any]:
        """
        Get detailed impact analysis for a configuration change event.

        Args:
            session: Database session
            change_event_id: Configuration change event ID

        Returns:
            Comprehensive impact analysis and visualization data
        """
        try:
            structlog.contextvars.bind_contextvars(
                operation="get_change_impact",
                event_id=str(change_event_id),
            )

            logger.info("Getting configuration change impact analysis")

            # Get change event with related data
            query = (
                select(ConfigurationChangeEvent)
                .where(ConfigurationChangeEvent.id == change_event_id)
                .options(selectinload(ConfigurationChangeEvent.snapshot))
            )

            result = await session.execute(query)
            event = result.scalar_one_or_none()

            if not event:
                raise ResourceNotFoundError(f"Change event not found: {change_event_id}")

            # Get device info
            device = await session.get(Device, event.device_id)

            # Build impact analysis
            impact_data = {
                "event_id": str(event.id),
                "device_id": str(event.device_id),
                "device_name": device.hostname if device else "Unknown",
                "timestamp": event.timestamp.isoformat(),
                "file_path": event.file_path,
                "change_type": event.change_type,
                "risk_level": event.risk_level,
                "triggered_by": event.triggered_by,
                "impact_summary": event.impact_summary,
                "affected_services": event.affected_services,
                "rollback_available": event.rollback_available,
                "confidence_score": event.confidence_score,
                "metadata": event.metadata,
            }

            # Add snapshot information if available
            if event.snapshot:
                impact_data["snapshot"] = {
                    "id": str(event.snapshot.id),
                    "content_hash": event.snapshot.content_hash,
                    "file_size": event.snapshot.file_size,
                    "created_at": event.snapshot.created_at.isoformat(),
                }

            # Get related events in time window
            time_window = timedelta(minutes=30)
            related_query = (
                select(ConfigurationChangeEvent)
                .where(
                    and_(
                        ConfigurationChangeEvent.device_id == event.device_id,
                        ConfigurationChangeEvent.id != event.id,
                        ConfigurationChangeEvent.timestamp >= event.timestamp - time_window,
                        ConfigurationChangeEvent.timestamp <= event.timestamp + time_window,
                    )
                )
                .order_by(ConfigurationChangeEvent.timestamp)
            )

            result = await session.execute(related_query)
            related_events = list(result.scalars().all())

            impact_data["related_changes"] = [
                {
                    "event_id": str(related.id),
                    "timestamp": related.timestamp.isoformat(),
                    "file_path": related.file_path,
                    "change_type": related.change_type,
                    "risk_level": related.risk_level,
                    "time_delta": (related.timestamp - event.timestamp).total_seconds(),
                }
                for related in related_events
            ]

            # Add visualization data
            impact_data["visualization"] = {
                "timeline_position": await self._get_timeline_position(session, event),
                "change_frequency": await self._get_change_frequency(session, event),
                "risk_trend": await self._get_risk_trend(session, event),
            }

            return impact_data

        except Exception as e:
            logger.error("Error getting configuration change impact", error=str(e))
            raise

    async def _build_timeline_data(
        self,
        device: Device,
        events: list[ConfigurationChangeEvent],
        snapshots: list[ConfigurationSnapshot],
        include_content: bool,
        include_diffs: bool,
        file_path: str | None,
    ) -> dict[str, Any]:
        """Build comprehensive timeline visualization data."""

        # Combine events and snapshots into timeline
        timeline_items = []

        # Add events to timeline
        for event in events:
            timeline_items.append(
                {
                    "type": "event",
                    "id": str(event.id),
                    "timestamp": event.timestamp.isoformat(),
                    "file_path": event.file_path,
                    "change_type": event.change_type,
                    "risk_level": event.risk_level,
                    "triggered_by": event.triggered_by,
                    "impact_summary": event.impact_summary,
                    "affected_services": event.affected_services,
                    "confidence_score": event.confidence_score,
                }
            )

        # Add snapshots to timeline
        for snapshot in snapshots:
            item = {
                "type": "snapshot",
                "id": str(snapshot.id),
                "timestamp": snapshot.created_at.isoformat(),
                "file_path": snapshot.file_path,
                "change_type": snapshot.change_type,
                "content_hash": snapshot.content_hash,
                "file_size": snapshot.file_size,
            }

            if include_content and snapshot.content:
                item["content"] = snapshot.content

            timeline_items.append(item)

        # Sort by timestamp
        timeline_items.sort(key=lambda x: x["timestamp"], reverse=True)

        # Generate diffs between consecutive snapshots if requested
        if include_diffs:
            file_snapshots = [s for s in snapshots if not file_path or s.file_path == file_path]
            file_snapshots.sort(key=lambda x: x.created_at)

            for i in range(1, len(file_snapshots)):
                if file_snapshots[i].content and file_snapshots[i - 1].content:
                    diff = self.diff_generator.generate_unified_diff(
                        old_content=file_snapshots[i - 1].content,
                        new_content=file_snapshots[i].content,
                        old_name=f"{file_snapshots[i - 1].file_path} (previous)",
                        new_name=f"{file_snapshots[i].file_path} (current)",
                    )
                    # Find corresponding timeline item and add diff
                    for item in timeline_items:
                        if item.get("id") == str(file_snapshots[i].id):
                            item["diff"] = diff
                            item["diff_summary"] = self.diff_generator.get_diff_summary(diff)
                            break

        # Generate summary statistics
        stats = {
            "total_events": len(events),
            "total_snapshots": len(snapshots),
            "file_count": len(set(item["file_path"] for item in timeline_items)),
            "risk_distribution": {},
            "change_type_distribution": {},
            "activity_by_hour": [0] * 24,
        }

        # Calculate distributions
        for event in events:
            # Risk level distribution
            risk = event.risk_level
            stats["risk_distribution"][risk] = stats["risk_distribution"].get(risk, 0) + 1

            # Change type distribution
            change_type = event.change_type
            stats["change_type_distribution"][change_type] = (
                stats["change_type_distribution"].get(change_type, 0) + 1
            )

            # Activity by hour
            hour = event.timestamp.hour
            stats["activity_by_hour"][hour] += 1

        return {
            "device_id": str(device.id),
            "device_name": device.hostname,
            "timeline": timeline_items,
            "statistics": stats,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filters": {
                "file_path": file_path,
                "include_content": include_content,
                "include_diffs": include_diffs,
            },
        }

    def _assess_change_risk(
        self,
        snapshot1: ConfigurationSnapshot,
        snapshot2: ConfigurationSnapshot,
        diff_stats: dict[str, Any],
    ) -> str:
        """Assess risk level of configuration change based on diff analysis."""

        # Calculate risk factors
        size_change_ratio = 0
        if snapshot1.file_size and snapshot1.file_size > 0:
            size_change_ratio = (
                abs((snapshot2.file_size or 0) - snapshot1.file_size) / snapshot1.file_size
            )

        lines_changed = diff_stats.get("lines_added", 0) + diff_stats.get("lines_removed", 0)

        # Risk assessment logic
        if size_change_ratio > 0.5 or lines_changed > 100:
            return "high"
        elif size_change_ratio > 0.2 or lines_changed > 20:
            return "medium"
        else:
            return "low"

    async def _get_timeline_position(
        self, session: AsyncSession, event: ConfigurationChangeEvent
    ) -> dict[str, Any]:
        """Get timeline position context for an event."""

        # Get events before and after
        before_query = (
            select(func.count())
            .select_from(ConfigurationChangeEvent)
            .where(
                and_(
                    ConfigurationChangeEvent.device_id == event.device_id,
                    ConfigurationChangeEvent.timestamp < event.timestamp,
                )
            )
        )

        after_query = (
            select(func.count())
            .select_from(ConfigurationChangeEvent)
            .where(
                and_(
                    ConfigurationChangeEvent.device_id == event.device_id,
                    ConfigurationChangeEvent.timestamp > event.timestamp,
                )
            )
        )

        before_result = await session.execute(before_query)
        after_result = await session.execute(after_query)

        before_count = before_result.scalar()
        after_count = after_result.scalar()
        total_count = before_count + after_count + 1

        return {
            "position": before_count + 1,
            "total": total_count,
            "percentage": ((before_count + 1) / total_count) * 100 if total_count > 0 else 0,
        }

    async def _get_change_frequency(
        self, session: AsyncSession, event: ConfigurationChangeEvent
    ) -> dict[str, Any]:
        """Get change frequency analysis around an event."""

        # Look at 7 days before and after
        window = timedelta(days=7)

        query = (
            select(func.count())
            .select_from(ConfigurationChangeEvent)
            .where(
                and_(
                    ConfigurationChangeEvent.device_id == event.device_id,
                    ConfigurationChangeEvent.file_path == event.file_path,
                    ConfigurationChangeEvent.timestamp >= event.timestamp - window,
                    ConfigurationChangeEvent.timestamp <= event.timestamp + window,
                )
            )
        )

        result = await session.execute(query)
        changes_in_window = result.scalar()

        return {
            "changes_in_14_days": changes_in_window,
            "frequency_score": "high"
            if changes_in_window > 10
            else "medium"
            if changes_in_window > 3
            else "low",
        }

    async def _get_risk_trend(
        self, session: AsyncSession, event: ConfigurationChangeEvent
    ) -> dict[str, Any]:
        """Get risk trend analysis for recent changes."""

        # Get last 10 events for this file
        query = (
            select(ConfigurationChangeEvent.risk_level)
            .where(
                and_(
                    ConfigurationChangeEvent.device_id == event.device_id,
                    ConfigurationChangeEvent.file_path == event.file_path,
                    ConfigurationChangeEvent.timestamp <= event.timestamp,
                )
            )
            .order_by(desc(ConfigurationChangeEvent.timestamp))
            .limit(10)
        )

        result = await session.execute(query)
        risk_levels = list(result.scalars().all())

        risk_scores = {"low": 1, "medium": 2, "high": 3, "critical": 4, "urgent": 5}
        scores = [risk_scores.get(level, 1) for level in risk_levels]

        if len(scores) < 2:
            trend = "stable"
        else:
            avg_recent = sum(scores[:3]) / min(3, len(scores))
            avg_older = sum(scores[3:]) / max(1, len(scores) - 3)

            if avg_recent > avg_older * 1.2:
                trend = "increasing"
            elif avg_recent < avg_older * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"

        return {
            "trend": trend,
            "recent_risk_levels": risk_levels[:5],
            "average_risk_score": sum(scores) / len(scores) if scores else 1,
        }


# Singleton service instance
_timeline_service: ConfigurationTimelineService | None = None


async def get_configuration_timeline_service() -> ConfigurationTimelineService:
    """Get the singleton configuration timeline service instance."""
    global _timeline_service
    if _timeline_service is None:
        _timeline_service = ConfigurationTimelineService()
    return _timeline_service


async def cleanup_configuration_timeline_service() -> None:
    """Clean up the configuration timeline service."""
    global _timeline_service
    if _timeline_service is not None:
        _timeline_service = None
        logger.info("Configuration timeline service cleaned up")
