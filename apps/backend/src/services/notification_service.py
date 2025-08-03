"""Service layer for sending notifications via external services like Gotify."""

import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from enum import Enum

import httpx
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.config import get_settings, ExternalIntegrationSettings
from apps.backend.src.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class NotificationSeverity(str, Enum):
    """Notification severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationCategory(str, Enum):
    """Notification categories for organization"""

    SYSTEM = "system"
    CONTAINER = "container"
    STORAGE = "storage"
    NETWORK = "network"
    BACKUP = "backup"
    UPDATE = "update"
    HEALTH = "health"


class NotificationMessage(BaseModel):
    """Notification message structure"""

    title: str
    message: str
    severity: NotificationSeverity = NotificationSeverity.INFO
    category: NotificationCategory = NotificationCategory.SYSTEM
    device_id: Optional[UUID] = None
    device_hostname: Optional[str] = None
    metadata: Dict[str, Any] = {}
    timestamp: datetime = None

    def __init__(self, **kwargs):
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.now(timezone.utc)
        super().__init__(**kwargs)


class NotificationService:
    """Service for sending notifications to external systems"""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session
        self.settings = get_settings()
        self.integration_settings = ExternalIntegrationSettings()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def is_gotify_configured(self) -> bool:
        """Check if Gotify is properly configured"""
        return bool(self.integration_settings.gotify_url and self.integration_settings.gotify_token)

    async def send_notification(self, notification: NotificationMessage) -> bool:
        """Send a notification via all configured channels"""
        success = False

        # Try Gotify first
        if self.is_gotify_configured():
            try:
                await self._send_gotify_notification(notification)
                success = True
                logger.info(f"Notification sent via Gotify: {notification.title}")
            except Exception as e:
                logger.error(f"Failed to send Gotify notification: {e}")

        # Could add more notification channels here (email, Slack, Discord, etc.)

        # Log notification locally as fallback
        if not success:
            self._log_notification(notification)
            logger.warning(
                f"Notification logged locally (no external services configured): {notification.title}"
            )

        return success

    async def _send_gotify_notification(self, notification: NotificationMessage) -> None:
        """Send notification to Gotify server"""
        if not self.is_gotify_configured():
            raise ExternalServiceError("Gotify is not configured")

        # Map severity to Gotify priority
        priority_map = {
            NotificationSeverity.INFO: 1,
            NotificationSeverity.WARNING: 5,
            NotificationSeverity.ERROR: 8,
            NotificationSeverity.CRITICAL: 10,
        }

        # Prepare message with metadata
        message_text = notification.message
        if notification.device_hostname:
            message_text = f"[{notification.device_hostname}] {message_text}"

        # Add metadata as extras
        extras = {
            "category": notification.category.value,
            "timestamp": notification.timestamp.isoformat(),
            "severity": notification.severity.value,
        }

        if notification.device_id:
            extras["device_id"] = str(notification.device_id)

        if notification.metadata:
            extras.update(notification.metadata)

        # Prepare Gotify message
        gotify_payload = {
            "title": notification.title,
            "message": message_text,
            "priority": priority_map.get(notification.severity, 1),
            "extras": extras,
        }

        # Send to Gotify
        url = f"{self.integration_settings.gotify_url.rstrip('/')}/message"
        headers = {
            "X-Gotify-Key": self.integration_settings.gotify_token,
            "Content-Type": "application/json",
        }

        try:
            response = await self.client.post(url, json=gotify_payload, headers=headers)
            response.raise_for_status()

        except httpx.HTTPError as e:
            raise ExternalServiceError(f"Failed to send Gotify notification: {e}")

    def _log_notification(self, notification: NotificationMessage) -> None:
        """Log notification locally when external services are unavailable"""
        log_data = {
            "title": notification.title,
            "message": notification.message,
            "severity": notification.severity.value,
            "category": notification.category.value,
            "device_hostname": notification.device_hostname,
            "timestamp": notification.timestamp.isoformat(),
            "metadata": notification.metadata,
        }

        # Use appropriate log level based on severity
        if notification.severity == NotificationSeverity.CRITICAL:
            logger.critical(f"NOTIFICATION: {json.dumps(log_data, indent=2)}")
        elif notification.severity == NotificationSeverity.ERROR:
            logger.error(f"NOTIFICATION: {json.dumps(log_data, indent=2)}")
        elif notification.severity == NotificationSeverity.WARNING:
            logger.warning(f"NOTIFICATION: {json.dumps(log_data, indent=2)}")
        else:
            logger.info(f"NOTIFICATION: {json.dumps(log_data, indent=2)}")

    async def send_device_offline_notification(self, device_id: UUID, hostname: str) -> None:
        """Send device offline notification"""
        notification = NotificationMessage(
            title="Device Offline",
            message=f"Device {hostname} is no longer reachable via SSH",
            severity=NotificationSeverity.WARNING,
            category=NotificationCategory.SYSTEM,
            device_id=device_id,
            device_hostname=hostname,
            metadata={"event_type": "device_offline"},
        )
        await self.send_notification(notification)

    async def send_device_online_notification(self, device_id: UUID, hostname: str) -> None:
        """Send device back online notification"""
        notification = NotificationMessage(
            title="Device Online",
            message=f"Device {hostname} is back online and reachable",
            severity=NotificationSeverity.INFO,
            category=NotificationCategory.SYSTEM,
            device_id=device_id,
            device_hostname=hostname,
            metadata={"event_type": "device_online"},
        )
        await self.send_notification(notification)

    async def send_container_down_notification(
        self, device_id: UUID, hostname: str, container_name: str
    ) -> None:
        """Send container down notification"""
        notification = NotificationMessage(
            title="Container Down",
            message=f"Container '{container_name}' is no longer running",
            severity=NotificationSeverity.WARNING,
            category=NotificationCategory.CONTAINER,
            device_id=device_id,
            device_hostname=hostname,
            metadata={"event_type": "container_down", "container_name": container_name},
        )
        await self.send_notification(notification)

    async def send_high_resource_usage_notification(
        self,
        device_id: UUID,
        hostname: str,
        resource_type: str,
        usage_percent: float,
        threshold: float,
    ) -> None:
        """Send high resource usage notification"""
        notification = NotificationMessage(
            title=f"High {resource_type.title()} Usage",
            message=f"{resource_type.title()} usage is at {usage_percent:.1f}% (threshold: {threshold:.1f}%)",
            severity=NotificationSeverity.WARNING
            if usage_percent < 90
            else NotificationSeverity.ERROR,
            category=NotificationCategory.SYSTEM,
            device_id=device_id,
            device_hostname=hostname,
            metadata={
                "event_type": "high_resource_usage",
                "resource_type": resource_type,
                "usage_percent": usage_percent,
                "threshold": threshold,
            },
        )
        await self.send_notification(notification)

    async def send_drive_health_notification(
        self,
        device_id: UUID,
        hostname: str,
        drive_name: str,
        health_status: str,
        details: Optional[str] = None,
    ) -> None:
        """Send drive health alert notification"""
        severity = (
            NotificationSeverity.CRITICAL
            if health_status.lower() in ["failed", "failing"]
            else NotificationSeverity.WARNING
        )

        message = f"Drive {drive_name} health status: {health_status}"
        if details:
            message += f" - {details}"

        notification = NotificationMessage(
            title="Drive Health Alert",
            message=message,
            severity=severity,
            category=NotificationCategory.STORAGE,
            device_id=device_id,
            device_hostname=hostname,
            metadata={
                "event_type": "drive_health_alert",
                "drive_name": drive_name,
                "health_status": health_status,
                "details": details,
            },
        )
        await self.send_notification(notification)

    async def send_backup_failure_notification(
        self, device_id: UUID, hostname: str, backup_name: str, error_message: str
    ) -> None:
        """Send backup failure notification"""
        notification = NotificationMessage(
            title="Backup Failed",
            message=f"Backup '{backup_name}' failed: {error_message}",
            severity=NotificationSeverity.ERROR,
            category=NotificationCategory.BACKUP,
            device_id=device_id,
            device_hostname=hostname,
            metadata={
                "event_type": "backup_failure",
                "backup_name": backup_name,
                "error_message": error_message,
            },
        )
        await self.send_notification(notification)

    async def send_zfs_scrub_notification(
        self, device_id: UUID, hostname: str, pool_name: str, status: str, errors_found: int = 0
    ) -> None:
        """Send ZFS scrub completion notification"""
        severity = NotificationSeverity.ERROR if errors_found > 0 else NotificationSeverity.INFO

        message = f"ZFS scrub completed on pool '{pool_name}' - Status: {status}"
        if errors_found > 0:
            message += f" ({errors_found} errors found)"

        notification = NotificationMessage(
            title="ZFS Scrub Completed",
            message=message,
            severity=severity,
            category=NotificationCategory.STORAGE,
            device_id=device_id,
            device_hostname=hostname,
            metadata={
                "event_type": "zfs_scrub_complete",
                "pool_name": pool_name,
                "status": status,
                "errors_found": errors_found,
            },
        )
        await self.send_notification(notification)

    async def send_updates_available_notification(
        self, device_id: UUID, hostname: str, total_updates: int, security_updates: int = 0
    ) -> None:
        """Send system updates available notification"""
        severity = (
            NotificationSeverity.WARNING if security_updates > 0 else NotificationSeverity.INFO
        )

        message = f"{total_updates} system updates available"
        if security_updates > 0:
            message += f" ({security_updates} security updates)"

        notification = NotificationMessage(
            title="System Updates Available",
            message=message,
            severity=severity,
            category=NotificationCategory.UPDATE,
            device_id=device_id,
            device_hostname=hostname,
            metadata={
                "event_type": "updates_available",
                "total_updates": total_updates,
                "security_updates": security_updates,
            },
        )
        await self.send_notification(notification)

    async def send_custom_notification(
        self,
        title: str,
        message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO,
        category: NotificationCategory = NotificationCategory.SYSTEM,
        device_id: Optional[UUID] = None,
        device_hostname: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send a custom notification with arbitrary content"""
        notification = NotificationMessage(
            title=title,
            message=message,
            severity=severity,
            category=category,
            device_id=device_id,
            device_hostname=device_hostname,
            metadata=metadata or {},
        )
        await self.send_notification(notification)

    async def test_notification_channels(self) -> Dict[str, bool]:
        """Test all configured notification channels"""
        results = {}

        # Test Gotify
        if self.is_gotify_configured():
            try:
                test_notification = NotificationMessage(
                    title="Test Notification",
                    message="This is a test notification from Infrastructure Monitor",
                    severity=NotificationSeverity.INFO,
                    category=NotificationCategory.SYSTEM,
                    metadata={"test": True},
                )
                await self._send_gotify_notification(test_notification)
                results["gotify"] = True
            except Exception as e:
                logger.error(f"Gotify test failed: {e}")
                results["gotify"] = False
        else:
            results["gotify"] = False

        return results


# Factory function for dependency injection
def get_notification_service(db: AsyncSession) -> NotificationService:
    """Create a notification service instance"""
    return NotificationService(db)
