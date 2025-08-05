"""
Destructive Action Manager

Manages the complete lifecycle of blocked destructive actions, from generating
confirmation requirements to processing user responses and executing approved actions.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any
from enum import Enum

from ..cache_manager import CacheManager
from ...core.exceptions import (
    ValidationError,
    CacheOperationError,
    AuthorizationError,
)

logger = logging.getLogger(__name__)


class OperationStatus(Enum):
    """Status of a destructive operation."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    FAILED = "failed"
    EXECUTED = "executed"
    CANCELLED = "cancelled"


class ConfirmationAttempt:
    """Represents a confirmation attempt with details."""

    def __init__(
        self, phrase: str, timestamp: datetime, success: bool, user_agent: str | None = None
    ):
        self.phrase = phrase
        self.timestamp = timestamp
        self.success = success
        self.user_agent = user_agent


class DestructiveActionManager:
    """
    Manages destructive action confirmation workflows and state.

    Features:
    - Multi-step confirmation flows with dynamic phrase generation
    - Timeout and attempt limiting
    - Comprehensive audit trails
    - Integration with existing cache infrastructure
    - Security-focused validation and logging
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        confirmation_timeout_seconds: int = 300,  # 5 minutes default
        max_global_attempts: int = 5,  # Global rate limiting
        cleanup_interval_seconds: int = 60,  # Cleanup every minute
    ):
        """
        Initialize the destructive action manager.

        Args:
            cache_manager: Cache manager for storing operation state
            confirmation_timeout_seconds: How long confirmations remain valid
            max_global_attempts: Maximum global confirmation attempts per minute
            cleanup_interval_seconds: How often to clean up expired operations
        """
        self.cache_manager = cache_manager
        self.confirmation_timeout_seconds = confirmation_timeout_seconds
        self.max_global_attempts = max_global_attempts
        self.cleanup_interval_seconds = cleanup_interval_seconds

        # Track global confirmation attempts for rate limiting
        self._global_attempts_key = "destructive_actions:global_attempts"

        logger.info(
            f"DestructiveActionManager initialized - timeout: {confirmation_timeout_seconds}s, "
            f"max_attempts: {max_global_attempts}"
        )

    async def block_and_require_confirmation(
        self, analysis: dict[str, Any], user_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Block a destructive action and generate confirmation requirements.

        Args:
            analysis: Complete risk analysis from RiskAssessmentEngine
            user_context: Optional user context for auditing

        Returns:
            Enhanced analysis with confirmation requirements and operation ID
        """
        # Generate unique operation ID
        operation_id = f"op_{uuid.uuid4().hex[:12]}"
        current_time = datetime.now(timezone.utc)

        # Generate confirmation phrase
        confirmation_phrase = self._generate_confirmation_phrase(analysis, user_context)

        # Determine escalation requirements
        escalation = analysis.get("confirmation_escalation", {})
        max_attempts = escalation.get("max_attempts", 3)
        requires_admin = escalation.get("requires_admin_approval", False)

        # Create operation state
        operation_state = {
            "operation_id": operation_id,
            "status": OperationStatus.PENDING.value,
            "analysis": analysis,
            "user_context": user_context or {},
            "confirmation_phrase": confirmation_phrase,
            "created_at": current_time.isoformat(),
            "expires_at": (
                current_time + timedelta(seconds=self.confirmation_timeout_seconds)
            ).isoformat(),
            "max_attempts": max_attempts,
            "current_attempts": 0,
            "requires_admin_approval": requires_admin,
            "confirmation_attempts": [],
            "metadata": {
                "device_hostname": analysis.get("device_context", {}).get("hostname", "unknown"),
                "action_type": analysis.get("action_type"),
                "risk_level": analysis.get("risk_level"),
                "user_agent": user_context.get("user_agent") if user_context else None,
                "source_ip": user_context.get("source_ip") if user_context else None,
            },
        }

        # Store operation state in cache
        try:
            await self.cache_manager.set(
                operation="destructive_action",
                device_id=operation_id,
                value=operation_state,
                data_type="destructive_operation",
                ttl_seconds=self.confirmation_timeout_seconds,
                metadata={
                    "operation_type": "destructive_action_confirmation",
                    "risk_level": analysis.get("risk_level"),
                    "action_type": analysis.get("action_type"),
                },
            )
        except Exception as e:
            logger.error(f"Failed to store operation state for {operation_id}: {e}")
            raise CacheOperationError(f"Could not initialize confirmation process: {e}") from e

        # Create response with confirmation requirements
        confirmation_response = {
            **analysis,  # Include all original analysis
            "blocked": True,
            "operation_id": operation_id,
            "confirmation_phrase": confirmation_phrase,
            "expires_in_seconds": self.confirmation_timeout_seconds,
            "expires_at": (
                current_time + timedelta(seconds=self.confirmation_timeout_seconds)
            ).isoformat(),
            "max_attempts": max_attempts,
            "requires_admin_approval": requires_admin,
            "confirmation_instructions": self._generate_confirmation_instructions(
                analysis, confirmation_phrase, requires_admin
            ),
        }

        logger.warning(
            f"Destructive action BLOCKED - Operation: {operation_id}, "
            f"Action: {analysis.get('action_type')}, "
            f"Risk: {analysis.get('risk_level')}, "
            f"Device: {analysis.get('device_context', {}).get('hostname', 'unknown')}"
        )

        return confirmation_response

    async def process_confirmation(
        self, operation_id: str, user_phrase: str, user_context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Process a user's confirmation attempt.

        Args:
            operation_id: The operation ID to confirm
            user_phrase: The confirmation phrase provided by the user
            user_context: Optional user context for auditing

        Returns:
            Result of the confirmation attempt
        """
        # Rate limiting check
        if not await self._check_global_rate_limit():
            logger.warning(f"Global rate limit exceeded for confirmation attempts")
            return {
                "status": "error",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many confirmation attempts. Please wait before trying again.",
            }

        # Retrieve operation state
        operation_state, found = await self.cache_manager.get(
            operation="destructive_action",
            device_id=operation_id,
            data_type="destructive_operation",
        )

        if not found or not operation_state:
            logger.warning(f"Confirmation attempt for unknown/expired operation: {operation_id}")
            return {
                "status": "error",
                "error_code": "OPERATION_NOT_FOUND",
                "message": "Operation not found or has expired. Please retry the original command.",
            }

        # Check if operation is still pending
        if operation_state["status"] != OperationStatus.PENDING.value:
            return {
                "status": "error",
                "error_code": "OPERATION_NOT_PENDING",
                "message": f"Operation is in '{operation_state['status']}' state and cannot be confirmed.",
            }

        # Check if max attempts reached
        if operation_state["current_attempts"] >= operation_state["max_attempts"]:
            await self._mark_operation_failed(operation_id, "MAX_ATTEMPTS_EXCEEDED")
            return {
                "status": "error",
                "error_code": "MAX_ATTEMPTS_EXCEEDED",
                "message": f"Maximum confirmation attempts ({operation_state['max_attempts']}) exceeded.",
            }

        # Record confirmation attempt
        attempt = ConfirmationAttempt(
            phrase=user_phrase,
            timestamp=datetime.now(timezone.utc),
            success=False,  # Will be updated if successful
            user_agent=user_context.get("user_agent") if user_context else None,
        )

        operation_state["current_attempts"] += 1
        operation_state["confirmation_attempts"].append(
            {
                "phrase": user_phrase[:50] + "..."
                if len(user_phrase) > 50
                else user_phrase,  # Truncate for security
                "timestamp": attempt.timestamp.isoformat(),
                "success": False,
                "user_agent": attempt.user_agent,
            }
        )

        # Validate confirmation phrase
        expected_phrase = operation_state["confirmation_phrase"]
        if not self._validate_confirmation_phrase(user_phrase, expected_phrase):
            # Update operation state with failed attempt
            await self._update_operation_state(operation_id, operation_state)

            logger.warning(
                f"Invalid confirmation phrase for {operation_id} - "
                f"Attempt {operation_state['current_attempts']}/{operation_state['max_attempts']}"
            )

            return {
                "status": "error",
                "error_code": "INVALID_PHRASE",
                "message": f"Confirmation phrase does not match. "
                f"Attempts: {operation_state['current_attempts']}/{operation_state['max_attempts']}",
                "expected_phrase": expected_phrase,  # Help user with correct phrase
            }

        # Confirmation successful!
        operation_state["confirmation_attempts"][-1]["success"] = True
        operation_state["status"] = OperationStatus.CONFIRMED.value
        operation_state["confirmed_at"] = datetime.now(timezone.utc).isoformat()
        operation_state["confirmed_by"] = user_context or {}

        # Update operation state
        await self._update_operation_state(operation_id, operation_state)

        logger.info(
            f"Destructive action CONFIRMED - Operation: {operation_id}, "
            f"Action: {operation_state['analysis'].get('action_type')}, "
            f"Device: {operation_state['metadata'].get('device_hostname')}"
        )

        return {
            "status": "confirmed",
            "operation_id": operation_id,
            "message": "Destructive action confirmed. The operation can now be executed.",
            "analysis": operation_state["analysis"],
            "confirmed_at": operation_state["confirmed_at"],
            "execution_ready": True,
        }

    async def get_operation_status(self, operation_id: str) -> dict[str, Any] | None:
        """Get the current status of an operation."""
        operation_state, found = await self.cache_manager.get(
            operation="destructive_action",
            device_id=operation_id,
            data_type="destructive_operation",
        )

        if not found:
            return None

        return {
            "operation_id": operation_id,
            "status": operation_state["status"],
            "created_at": operation_state["created_at"],
            "expires_at": operation_state["expires_at"],
            "current_attempts": operation_state["current_attempts"],
            "max_attempts": operation_state["max_attempts"],
            "action_type": operation_state["analysis"].get("action_type"),
            "risk_level": operation_state["analysis"].get("risk_level"),
            "device_hostname": operation_state["metadata"].get("device_hostname"),
            "requires_admin_approval": operation_state.get("requires_admin_approval", False),
        }

    async def cancel_operation(self, operation_id: str, reason: str = "user_cancelled") -> bool:
        """Cancel a pending operation."""
        operation_state, found = await self.cache_manager.get(
            operation="destructive_action",
            device_id=operation_id,
            data_type="destructive_operation",
        )

        if not found or operation_state["status"] != OperationStatus.PENDING.value:
            return False

        operation_state["status"] = OperationStatus.CANCELLED.value
        operation_state["cancelled_at"] = datetime.now(timezone.utc).isoformat()
        operation_state["cancellation_reason"] = reason

        await self._update_operation_state(operation_id, operation_state)

        logger.info(f"Operation {operation_id} cancelled: {reason}")
        return True

    async def mark_operation_executed(
        self, operation_id: str, execution_result: dict[str, Any]
    ) -> bool:
        """Mark an operation as executed with results."""
        operation_state, found = await self.cache_manager.get(
            operation="destructive_action",
            device_id=operation_id,
            data_type="destructive_operation",
        )

        if not found or operation_state["status"] != OperationStatus.CONFIRMED.value:
            return False

        operation_state["status"] = OperationStatus.EXECUTED.value
        operation_state["executed_at"] = datetime.now(timezone.utc).isoformat()
        operation_state["execution_result"] = execution_result

        await self._update_operation_state(operation_id, operation_state)

        logger.info(
            f"Operation {operation_id} executed - Success: {execution_result.get('success', False)}"
        )
        return True

    def _generate_confirmation_phrase(
        self, analysis: dict[str, Any], user_context: dict[str, Any] | None = None
    ) -> str:
        """Generate a unique confirmation phrase for the operation."""
        action_type = analysis.get("action_type", "unknown")
        device_name = analysis.get("device_context", {}).get("hostname", "device")
        risk_level = analysis.get("risk_level", "unknown")
        affected_count = analysis.get("blast_radius", {}).get("estimated_count", 0)

        # Create context-specific phrase
        if affected_count > 1:
            phrase = f"yes, destroy {affected_count} items via {action_type} on {device_name}"
        else:
            phrase = f"yes, execute {action_type} on {device_name} at {risk_level.lower()} risk"

        # Add timestamp component for uniqueness
        timestamp_component = datetime.now(timezone.utc).strftime("%H%M")
        phrase = f"{phrase} at {timestamp_component}"

        return phrase

    def _generate_confirmation_instructions(
        self, analysis: dict[str, Any], confirmation_phrase: str, requires_admin: bool
    ) -> list[str]:
        """Generate user-friendly confirmation instructions."""
        instructions = [
            "🚨 DESTRUCTIVE ACTION DETECTED",
            "",
            f"Action: {analysis.get('action_type', 'unknown')}",
            f"Risk Level: {analysis.get('risk_level', 'unknown')}",
            f"Impact: {analysis.get('impact_summary', 'Unknown impact')}",
        ]

        if analysis.get("safety_warnings"):
            instructions.append("")
            instructions.append("⚠️  WARNINGS:")
            for warning in analysis["safety_warnings"]:
                instructions.append(f"   {warning}")

        if analysis.get("alternative_suggestions"):
            instructions.append("")
            instructions.append("💡 SAFER ALTERNATIVES:")
            for suggestion in analysis["alternative_suggestions"][:3]:  # Limit to top 3
                instructions.append(f"   • {suggestion}")

        instructions.extend(
            [
                "",
                "📋 SAFETY CHECKLIST:",
            ]
        )

        if analysis.get("safety_checklist"):
            for item in analysis["safety_checklist"]:
                instructions.append(f"   {item}")

        instructions.extend(
            [
                "",
                "To proceed, you must type the following phrase EXACTLY:",
                f'"{confirmation_phrase}"',
            ]
        )

        if requires_admin:
            instructions.append("")
            instructions.append(
                "🔒 ADMIN APPROVAL REQUIRED - This action requires administrator confirmation"
            )

        return instructions

    def _validate_confirmation_phrase(self, user_phrase: str, expected_phrase: str) -> bool:
        """Validate the confirmation phrase with some flexibility."""
        # Normalize both phrases
        user_normalized = user_phrase.strip().lower()
        expected_normalized = expected_phrase.strip().lower()

        # Exact match preferred
        if user_normalized == expected_normalized:
            return True

        # Allow for minor variations (remove extra spaces, punctuation)
        import re

        user_cleaned = re.sub(r"[^\w\s]", "", user_normalized)
        expected_cleaned = re.sub(r"[^\w\s]", "", expected_normalized)

        user_cleaned = " ".join(user_cleaned.split())  # Normalize whitespace
        expected_cleaned = " ".join(expected_cleaned.split())

        return user_cleaned == expected_cleaned

    async def _check_global_rate_limit(self) -> bool:
        """Check if we're within global rate limits for confirmation attempts."""
        # Simple rate limiting: max attempts per minute
        current_minute = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
        rate_limit_key = f"{self._global_attempts_key}:{current_minute}"

        attempts, found = await self.cache_manager.get(
            operation="rate_limit", device_id=rate_limit_key, data_type="rate_limit"
        )

        current_attempts = attempts if found else 0

        if current_attempts >= self.max_global_attempts:
            return False

        # Increment attempt counter
        await self.cache_manager.set(
            operation="rate_limit",
            device_id=rate_limit_key,
            value=current_attempts + 1,
            data_type="rate_limit",
            ttl_seconds=60,  # Expire after 1 minute
        )

        return True

    async def _update_operation_state(
        self, operation_id: str, operation_state: dict[str, Any]
    ) -> None:
        """Update operation state in cache."""
        try:
            await self.cache_manager.set(
                operation="destructive_action",
                device_id=operation_id,
                value=operation_state,
                data_type="destructive_operation",
                ttl_seconds=self.confirmation_timeout_seconds,
            )
        except Exception as e:
            logger.error(f"Failed to update operation state for {operation_id}: {e}")
            raise CacheOperationError(f"Could not update operation state: {e}") from e

    async def _mark_operation_failed(self, operation_id: str, reason: str) -> None:
        """Mark operation as failed and remove from cache."""
        operation_state, found = await self.cache_manager.get(
            operation="destructive_action",
            device_id=operation_id,
            data_type="destructive_operation",
        )

        if found:
            operation_state["status"] = OperationStatus.FAILED.value
            operation_state["failed_at"] = datetime.now(timezone.utc).isoformat()
            operation_state["failure_reason"] = reason

            await self._update_operation_state(operation_id, operation_state)

            logger.warning(f"Operation {operation_id} marked as failed: {reason}")

    async def cleanup_expired_operations(self) -> int:
        """Clean up expired operations (called by background task)."""
        # This would be implemented by scanning cache entries
        # For now, we rely on the cache manager's TTL mechanism
        return 0

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about the action manager."""
        # This would query the cache for operation statistics
        return {
            "confirmation_timeout_seconds": self.confirmation_timeout_seconds,
            "max_global_attempts": self.max_global_attempts,
            # TODO: Add more statistics from cache entries
        }
