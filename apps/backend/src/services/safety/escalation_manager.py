"""
Escalation Manager

Handles progressive escalation of safety violations, failed confirmations, and
repeated destructive action attempts. Provides lockout mechanisms and notification
systems for safety violations.
"""

import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EscalationLevel(Enum):
    """Escalation severity levels."""

    NONE = "none"
    WARNING = "warning"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    LOCKOUT = "lockout"


class EscalationAction(Enum):
    """Actions taken during escalation."""

    LOG_WARNING = "log_warning"
    SEND_NOTIFICATION = "send_notification"
    TEMPORARY_LOCKOUT = "temporary_lockout"
    EXTENDED_LOCKOUT = "extended_lockout"
    PERMANENT_LOCKOUT = "permanent_lockout"
    ADMIN_NOTIFICATION = "admin_notification"


class ViolationType(Enum):
    """Types of safety violations."""

    FAILED_CONFIRMATION = "failed_confirmation"
    INVALID_PHRASE = "invalid_phrase"
    TIMEOUT_EXCEEDED = "timeout_exceeded"
    ATTEMPT_LIMIT_EXCEEDED = "attempt_limit_exceeded"
    UNAUTHORIZED_BYPASS = "unauthorized_bypass"
    SAFETY_CHECK_FAILURE = "safety_check_failure"


class EscalationManager:
    """
    Manages escalation procedures for safety violations and failed confirmations.

    Features:
    - Progressive escalation based on violation history
    - Temporary and permanent lockout mechanisms
    - Notification system for failed confirmations
    - Device-specific escalation policies
    - Recovery procedures for locked accounts
    """

    def __init__(self):
        """Initialize the escalation manager."""
        # In-memory storage for violation tracking (would be database in production)
        self.violation_history: dict[str, list[dict[str, Any]]] = {}
        self.lockout_status: dict[str, dict[str, Any]] = {}

        # Escalation thresholds
        self.escalation_thresholds = {
            EscalationLevel.WARNING: 3,  # 3 violations in window
            EscalationLevel.MODERATE: 5,  # 5 violations in window
            EscalationLevel.HIGH: 8,  # 8 violations in window
            EscalationLevel.CRITICAL: 12,  # 12 violations in window
            EscalationLevel.LOCKOUT: 15,  # 15 violations triggers lockout
        }

        # Time windows for violation counting (in minutes)
        self.violation_windows = {
            EscalationLevel.WARNING: 30,  # 30 minutes
            EscalationLevel.MODERATE: 60,  # 1 hour
            EscalationLevel.HIGH: 180,  # 3 hours
            EscalationLevel.CRITICAL: 720,  # 12 hours
            EscalationLevel.LOCKOUT: 1440,  # 24 hours
        }

        # Lockout durations (in minutes)
        self.lockout_durations = {
            EscalationLevel.WARNING: 0,  # No lockout
            EscalationLevel.MODERATE: 5,  # 5 minutes
            EscalationLevel.HIGH: 30,  # 30 minutes
            EscalationLevel.CRITICAL: 120,  # 2 hours
            EscalationLevel.LOCKOUT: 1440,  # 24 hours
        }

        logger.info("EscalationManager initialized")

    async def record_violation(
        self,
        device_id: str,
        user_context: dict[str, Any],
        violation_type: ViolationType,
        violation_details: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Record a safety violation and determine escalation response.

        Args:
            device_id: Target device identifier
            user_context: User performing the action
            violation_type: Type of violation
            violation_details: Additional violation information

        Returns:
            Escalation response with actions taken
        """
        logger.info(f"Recording {violation_type.value} violation for device {device_id}")

        violation_key = f"{device_id}:{user_context.get('user_id', 'unknown')}"

        # Record the violation
        violation_record = {
            "timestamp": datetime.now(timezone.utc),
            "device_id": device_id,
            "user_context": user_context,
            "violation_type": violation_type,
            "violation_details": violation_details,
        }

        if violation_key not in self.violation_history:
            self.violation_history[violation_key] = []

        self.violation_history[violation_key].append(violation_record)

        # Determine current escalation level
        escalation_level = self._calculate_escalation_level(violation_key)

        # Execute escalation actions
        escalation_response = await self._execute_escalation_actions(
            violation_key, escalation_level, violation_record
        )

        logger.info(f"Violation escalated to {escalation_level.value} level")

        return escalation_response

    async def check_lockout_status(
        self, device_id: str, user_context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Check if a user/device combination is currently locked out.

        Args:
            device_id: Target device identifier
            user_context: User context information

        Returns:
            Lockout status information
        """
        violation_key = f"{device_id}:{user_context.get('user_id', 'unknown')}"

        if violation_key not in self.lockout_status:
            return {
                "locked_out": False,
                "lockout_level": EscalationLevel.NONE,
                "lockout_expires_at": None,
                "minutes_remaining": 0,
            }

        lockout_info = self.lockout_status[violation_key]
        expires_at = lockout_info["expires_at"]

        # Check if lockout has expired
        if datetime.now(timezone.utc) >= expires_at:
            # Clear expired lockout
            del self.lockout_status[violation_key]
            logger.info(f"Lockout expired for {violation_key}")

            return {
                "locked_out": False,
                "lockout_level": EscalationLevel.NONE,
                "lockout_expires_at": None,
                "minutes_remaining": 0,
            }

        # Calculate remaining time
        remaining_time = expires_at - datetime.now(timezone.utc)
        minutes_remaining = int(remaining_time.total_seconds() / 60)

        return {
            "locked_out": True,
            "lockout_level": lockout_info["level"],
            "lockout_expires_at": expires_at.isoformat(),
            "minutes_remaining": minutes_remaining,
            "violation_count": lockout_info["violation_count"],
        }

    async def request_lockout_override(
        self,
        device_id: str,
        user_context: dict[str, Any],
        override_reason: str,
        admin_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Request administrative override of lockout status.

        Args:
            device_id: Target device identifier
            user_context: Locked out user context
            override_reason: Reason for override request
            admin_context: Administrator requesting override

        Returns:
            Override processing result
        """
        violation_key = f"{device_id}:{user_context.get('user_id', 'unknown')}"

        override_request = {
            "timestamp": datetime.now(timezone.utc),
            "device_id": device_id,
            "user_context": user_context,
            "admin_context": admin_context,
            "override_reason": override_reason,
            "status": "pending",
        }

        logger.info(
            f"Lockout override requested for {violation_key} by admin {admin_context.get('admin_id')}"
        )

        # For immediate implementation, auto-approve overrides
        # In production, this would require proper admin authorization
        if violation_key in self.lockout_status:
            del self.lockout_status[violation_key]
            override_request["status"] = "approved"
            override_request["approved_at"] = datetime.now(timezone.utc)

            logger.info(f"Lockout override approved for {violation_key}")

            return {
                "override_approved": True,
                "override_request": override_request,
                "lockout_cleared": True,
            }
        else:
            return {
                "override_approved": False,
                "error": "No active lockout found",
                "override_request": override_request,
            }

    def _calculate_escalation_level(self, violation_key: str) -> EscalationLevel:
        """Calculate the current escalation level based on violation history."""
        if violation_key not in self.violation_history:
            return EscalationLevel.NONE

        violations = self.violation_history[violation_key]
        current_time = datetime.now(timezone.utc)

        # Count violations in different time windows
        for level in reversed(list(EscalationLevel)):
            if level == EscalationLevel.NONE:
                continue

            window_minutes = self.violation_windows[level]
            threshold = self.escalation_thresholds[level]
            cutoff_time = current_time - timedelta(minutes=window_minutes)

            recent_violations = [v for v in violations if v["timestamp"] >= cutoff_time]

            if len(recent_violations) >= threshold:
                return level

        return EscalationLevel.NONE

    async def _execute_escalation_actions(
        self,
        violation_key: str,
        escalation_level: EscalationLevel,
        violation_record: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute appropriate escalation actions based on level."""
        actions_taken = []

        # Always log the violation
        actions_taken.append(EscalationAction.LOG_WARNING)
        logger.warning(
            f"Safety violation escalated to {escalation_level.value}: "
            f"{violation_record['violation_type'].value} on device {violation_record['device_id']}"
        )

        # Level-specific actions
        if escalation_level == EscalationLevel.WARNING:
            actions_taken.append(EscalationAction.SEND_NOTIFICATION)
            await self._send_notification(violation_key, escalation_level, violation_record)

        elif escalation_level == EscalationLevel.MODERATE:
            actions_taken.extend(
                [EscalationAction.SEND_NOTIFICATION, EscalationAction.TEMPORARY_LOCKOUT]
            )
            await self._send_notification(violation_key, escalation_level, violation_record)
            await self._apply_lockout(violation_key, escalation_level)

        elif escalation_level == EscalationLevel.HIGH:
            actions_taken.extend(
                [
                    EscalationAction.SEND_NOTIFICATION,
                    EscalationAction.EXTENDED_LOCKOUT,
                    EscalationAction.ADMIN_NOTIFICATION,
                ]
            )
            await self._send_notification(violation_key, escalation_level, violation_record)
            await self._apply_lockout(violation_key, escalation_level)
            await self._send_admin_notification(violation_key, escalation_level, violation_record)

        elif escalation_level in [EscalationLevel.CRITICAL, EscalationLevel.LOCKOUT]:
            actions_taken.extend(
                [
                    EscalationAction.SEND_NOTIFICATION,
                    EscalationAction.PERMANENT_LOCKOUT,
                    EscalationAction.ADMIN_NOTIFICATION,
                ]
            )
            await self._send_notification(violation_key, escalation_level, violation_record)
            await self._apply_lockout(violation_key, escalation_level)
            await self._send_admin_notification(violation_key, escalation_level, violation_record)

        return {
            "escalation_level": escalation_level,
            "actions_taken": actions_taken,
            "violation_count": len(self.violation_history[violation_key]),
            "lockout_applied": escalation_level
            in [
                EscalationLevel.MODERATE,
                EscalationLevel.HIGH,
                EscalationLevel.CRITICAL,
                EscalationLevel.LOCKOUT,
            ],
            "admin_notified": escalation_level
            in [EscalationLevel.HIGH, EscalationLevel.CRITICAL, EscalationLevel.LOCKOUT],
        }

    async def _apply_lockout(self, violation_key: str, escalation_level: EscalationLevel):
        """Apply lockout based on escalation level."""
        lockout_duration = self.lockout_durations[escalation_level]
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=lockout_duration)

        self.lockout_status[violation_key] = {
            "level": escalation_level,
            "applied_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "duration_minutes": lockout_duration,
            "violation_count": len(self.violation_history[violation_key]),
        }

        logger.warning(
            f"Applied {escalation_level.value} lockout to {violation_key} "
            f"for {lockout_duration} minutes"
        )

    async def _send_notification(
        self,
        violation_key: str,
        escalation_level: EscalationLevel,
        violation_record: dict[str, Any],
    ):
        """Send notification about safety violation."""
        # In production, this would integrate with notification systems
        notification_message = (
            f"Safety violation detected: {violation_record['violation_type'].value} "
            f"on device {violation_record['device_id']} "
            f"escalated to {escalation_level.value} level"
        )

        logger.info(f"Would send notification: {notification_message}")

    async def _send_admin_notification(
        self,
        violation_key: str,
        escalation_level: EscalationLevel,
        violation_record: dict[str, Any],
    ):
        """Send administrative notification for high-level violations."""
        # In production, this would integrate with admin notification systems
        admin_message = (
            f"URGENT: High-level safety violation ({escalation_level.value}) "
            f"detected for {violation_key}. "
            f"Violation: {violation_record['violation_type'].value} "
            f"on device {violation_record['device_id']}. "
            f"Total violations: {len(self.violation_history[violation_key])}"
        )

        logger.warning(f"Would send admin notification: {admin_message}")

    def get_violation_statistics(self, device_id: str | None = None) -> dict[str, Any]:
        """Get violation statistics for analysis."""
        stats = {
            "total_violations": 0,
            "violations_by_type": {},
            "violations_by_device": {},
            "current_lockouts": 0,
            "escalation_levels": {level.value: 0 for level in EscalationLevel},
        }

        # Count violations
        for violation_key, violations in self.violation_history.items():
            if device_id and not violation_key.startswith(device_id):
                continue

            stats["total_violations"] += len(violations)

            for violation in violations:
                # Count by type
                vtype = violation["violation_type"].value
                stats["violations_by_type"][vtype] = stats["violations_by_type"].get(vtype, 0) + 1

                # Count by device
                dev_id = violation["device_id"]
                stats["violations_by_device"][dev_id] = (
                    stats["violations_by_device"].get(dev_id, 0) + 1
                )

            # Current escalation level
            current_level = self._calculate_escalation_level(violation_key)
            stats["escalation_levels"][current_level.value] += 1

        # Count current lockouts
        stats["current_lockouts"] = len(self.lockout_status)

        return stats

    def cleanup_expired_violations(self, cleanup_age_hours: int = 72):
        """Clean up old violation records to prevent memory issues."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=cleanup_age_hours)
        cleaned_keys = []

        for violation_key, violations in list(self.violation_history.items()):
            # Remove old violations
            recent_violations = [v for v in violations if v["timestamp"] >= cutoff_time]

            if recent_violations:
                self.violation_history[violation_key] = recent_violations
            else:
                del self.violation_history[violation_key]
                cleaned_keys.append(violation_key)

        logger.info(f"Cleaned up {len(cleaned_keys)} old violation records")
        return {"cleaned_records": len(cleaned_keys), "cleanup_age_hours": cleanup_age_hours}
