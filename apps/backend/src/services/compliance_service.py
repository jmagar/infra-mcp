"""
Configuration Compliance Service

Provides comprehensive configuration compliance checking and reporting capabilities.
Implements policy enforcement, compliance validation, and automated reporting.
"""

import asyncio
import logging
import re
import json
from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, text
from sqlalchemy.orm import selectinload

from ..core.database import get_async_session
from ..core.exceptions import (
    ValidationError,
    ResourceNotFoundError,
    BusinessLogicError,
)
from ..models.device import Device
from ..models.configuration import ConfigurationSnapshot
from ..models.compliance import (
    ComplianceRule,
    ComplianceCheck,
    ComplianceReport,
    ComplianceException,
)
from ..services.unified_data_collection import get_unified_data_collection_service

logger = structlog.get_logger(__name__)


class ComplianceRuleEngine:
    """
    Rule engine for evaluating compliance rules against configuration content.

    Supports multiple rule types including regex, JSON path, custom functions,
    and template-based validation.
    """

    def __init__(self):
        self.rule_evaluators = {
            "regex": self._evaluate_regex_rule,
            "json-path": self._evaluate_json_path_rule,
            "custom": self._evaluate_custom_rule,
            "template": self._evaluate_template_rule,
            "function": self._evaluate_function_rule,
        }

    async def evaluate_rule(
        self,
        rule: ComplianceRule,
        content: str,
        file_path: str,
        device_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate a compliance rule against configuration content.

        Args:
            rule: The compliance rule to evaluate
            content: Configuration file content
            file_path: Path to the configuration file
            device_metadata: Additional device context

        Returns:
            Evaluation result with status, details, and recommendations
        """
        try:
            structlog.contextvars.bind_contextvars(
                operation="evaluate_rule",
                rule_id=str(rule.id),
                rule_type=rule.rule_type,
                file_path=file_path,
            )

            logger.debug("Evaluating compliance rule")

            if rule.rule_type not in self.rule_evaluators:
                raise ValidationError(f"Unsupported rule type: {rule.rule_type}")

            evaluator = self.rule_evaluators[rule.rule_type]
            result = await evaluator(rule, content, file_path, device_metadata)

            # Add common metadata to result
            result.update(
                {
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type,
                    "severity": rule.severity,
                    "file_path": file_path,
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            return result

        except Exception as e:
            logger.error("Error evaluating compliance rule", error=str(e))
            return {
                "status": "error",
                "error_message": str(e),
                "compliance_score": 0,
                "violation_count": 0,
                "violation_details": {"error": str(e)},
            }

    async def _evaluate_regex_rule(
        self,
        rule: ComplianceRule,
        content: str,
        file_path: str,
        device_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate regex-based compliance rule."""

        rule_def = rule.rule_definition
        pattern = rule_def.get("pattern")
        match_type = rule_def.get("match_type", "should_match")  # should_match, should_not_match
        flags = rule_def.get("flags", [])

        if not pattern:
            raise ValidationError("Regex rule missing 'pattern' in rule_definition")

        # Build regex flags
        regex_flags = 0
        if "ignorecase" in flags:
            regex_flags |= re.IGNORECASE
        if "multiline" in flags:
            regex_flags |= re.MULTILINE
        if "dotall" in flags:
            regex_flags |= re.DOTALL

        try:
            compiled_pattern = re.compile(pattern, regex_flags)
            matches = compiled_pattern.findall(content)

            if match_type == "should_match":
                passed = len(matches) > 0
                violation_count = 0 if passed else 1
            else:  # should_not_match
                passed = len(matches) == 0
                violation_count = len(matches)

            return {
                "status": "pass" if passed else "fail",
                "compliance_score": 100 if passed else 0,
                "violation_count": violation_count,
                "violation_details": {
                    "pattern": pattern,
                    "match_type": match_type,
                    "matches_found": len(matches),
                    "matches": matches[:10] if matches else [],  # Limit to first 10 matches
                },
            }

        except re.error as e:
            raise ValidationError(f"Invalid regex pattern: {e}")

    async def _evaluate_json_path_rule(
        self,
        rule: ComplianceRule,
        content: str,
        file_path: str,
        device_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate JSON path-based compliance rule."""

        rule_def = rule.rule_definition
        json_path = rule_def.get("json_path")
        expected_value = rule.expected_value
        comparison = rule_def.get("comparison", "equals")  # equals, not_equals, contains, exists

        if not json_path:
            raise ValidationError("JSON path rule missing 'json_path' in rule_definition")

        try:
            # Parse JSON content
            if file_path.endswith((".json", ".yml", ".yaml")):
                if file_path.endswith(".json"):
                    data = json.loads(content)
                else:
                    import yaml

                    data = yaml.safe_load(content)
            else:
                # Try to extract JSON from other file types
                import json

                data = json.loads(content)

            # Simple JSON path evaluation (basic implementation)
            # For production, consider using jsonpath-ng library
            actual_value = self._extract_json_path_value(data, json_path)

            if comparison == "exists":
                passed = actual_value is not None
            elif comparison == "equals":
                passed = actual_value == expected_value
            elif comparison == "not_equals":
                passed = actual_value != expected_value
            elif comparison == "contains":
                passed = expected_value in str(actual_value) if actual_value else False
            else:
                raise ValidationError(f"Unsupported comparison type: {comparison}")

            return {
                "status": "pass" if passed else "fail",
                "compliance_score": 100 if passed else 0,
                "violation_count": 0 if passed else 1,
                "violation_details": {
                    "json_path": json_path,
                    "expected_value": expected_value,
                    "actual_value": actual_value,
                    "comparison": comparison,
                },
            }

        except (json.JSONDecodeError, yaml.YAMLError) as e:
            return {
                "status": "error",
                "error_message": f"Failed to parse file as JSON/YAML: {e}",
                "compliance_score": 0,
                "violation_count": 0,
            }

    async def _evaluate_custom_rule(
        self,
        rule: ComplianceRule,
        content: str,
        file_path: str,
        device_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate custom function-based compliance rule."""

        rule_def = rule.rule_definition
        function_name = rule_def.get("function")

        # This would be extended to support custom rule functions
        # For now, return a placeholder implementation
        return {
            "status": "skipped",
            "compliance_score": 100,
            "violation_count": 0,
            "violation_details": {
                "message": f"Custom rule evaluation not implemented: {function_name}",
            },
        }

    async def _evaluate_template_rule(
        self,
        rule: ComplianceRule,
        content: str,
        file_path: str,
        device_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate template-based compliance rule."""

        # Template-based rules would use Jinja2 templates for complex logic
        # For now, return a placeholder implementation
        return {
            "status": "skipped",
            "compliance_score": 100,
            "violation_count": 0,
            "violation_details": {
                "message": "Template rule evaluation not implemented",
            },
        }

    async def _evaluate_function_rule(
        self,
        rule: ComplianceRule,
        content: str,
        file_path: str,
        device_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Evaluate function-based compliance rule."""

        # Function-based rules would execute Python functions
        # For now, return a placeholder implementation
        return {
            "status": "skipped",
            "compliance_score": 100,
            "violation_count": 0,
            "violation_details": {
                "message": "Function rule evaluation not implemented",
            },
        }

    def _extract_json_path_value(self, data: dict[str, Any], json_path: str) -> Any:
        """Extract value from JSON data using simple path notation."""

        # Simple implementation - for production, use jsonpath-ng
        parts = json_path.split(".")
        current = data

        try:
            for part in parts:
                if "[" in part and part.endswith("]"):
                    # Handle array indices like "items[0]"
                    key, index_part = part.split("[")
                    index = int(index_part.rstrip("]"))
                    current = current[key][index]
                else:
                    current = current[part]
            return current
        except (KeyError, IndexError, TypeError):
            return None


class ComplianceService:
    """
    Main service for configuration compliance checking and reporting.

    Provides comprehensive compliance management including rule evaluation,
    exception handling, reporting, and remediation tracking.
    """

    def __init__(self):
        self.rule_engine = ComplianceRuleEngine()

    async def create_compliance_rule(
        self,
        session: AsyncSession,
        rule_data: dict[str, Any],
        created_by: str,
    ) -> ComplianceRule:
        """Create a new compliance rule."""

        try:
            structlog.contextvars.bind_contextvars(
                operation="create_compliance_rule",
                created_by=created_by,
            )

            logger.info("Creating new compliance rule")

            # Create rule instance
            rule = ComplianceRule(
                name=rule_data["name"],
                description=rule_data.get("description"),
                category=rule_data["category"],
                severity=rule_data["severity"],
                rule_type=rule_data["rule_type"],
                rule_definition=rule_data["rule_definition"],
                expected_value=rule_data.get("expected_value"),
                violation_message=rule_data["violation_message"],
                remediation_guidance=rule_data.get("remediation_guidance"),
                target_file_patterns=rule_data["target_file_patterns"],
                device_tags=rule_data.get("device_tags"),
                exclusions=rule_data.get("exclusions"),
                enabled=rule_data.get("enabled", True),
                enforce_mode=rule_data.get("enforce_mode", "monitor"),
                auto_remediate=rule_data.get("auto_remediate", False),
                check_frequency=rule_data.get("check_frequency", "daily"),
                grace_period_hours=rule_data.get("grace_period_hours", 0),
                created_by=created_by,
                metadata=rule_data.get("metadata"),
            )

            session.add(rule)
            await session.commit()
            await session.refresh(rule)

            logger.info("Compliance rule created successfully", rule_id=str(rule.id))
            return rule

        except Exception as e:
            await session.rollback()
            logger.error("Error creating compliance rule", error=str(e))
            raise

    async def check_device_compliance(
        self,
        session: AsyncSession,
        device_id: UUID,
        rule_ids: list[UUID] | None = None,
        force_refresh: bool = False,
    ) -> list[ComplianceCheck]:
        """
        Check compliance for all applicable rules on a specific device.

        Args:
            session: Database session
            device_id: Device to check compliance for
            rule_ids: Specific rules to check (None = all enabled rules)
            force_refresh: Force fresh configuration snapshots

        Returns:
            List of compliance check results
        """
        try:
            structlog.contextvars.bind_contextvars(
                operation="check_device_compliance",
                device_id=str(device_id),
            )

            logger.info("Checking device compliance")

            # Get device
            device = await session.get(Device, device_id)
            if not device:
                raise ResourceNotFoundError(f"Device not found: {device_id}")

            # Get applicable rules
            rules_query = select(ComplianceRule).where(ComplianceRule.enabled == True)
            if rule_ids:
                rules_query = rules_query.where(ComplianceRule.id.in_(rule_ids))

            result = await session.execute(rules_query)
            rules = list(result.scalars().all())

            logger.info(f"Found {len(rules)} applicable compliance rules")

            # Get fresh configuration snapshots if needed
            if force_refresh:
                unified_service = await get_unified_data_collection_service()
                await unified_service.collect_device_configurations(session, device_id)

            # Check each rule
            compliance_checks = []

            for rule in rules:
                # Check if device matches rule targeting
                if not self._device_matches_rule(device, rule):
                    logger.debug("Device does not match rule targeting", rule_id=str(rule.id))
                    continue

                # Get configuration snapshots for files matching rule patterns
                snapshots = await self._get_matching_snapshots(
                    session, device_id, rule.target_file_patterns
                )

                # Check compliance for each matching file
                for snapshot in snapshots:
                    # Check for exceptions
                    if await self._has_active_exception(
                        session, rule.id, device_id, snapshot.file_path
                    ):
                        logger.debug(
                            "Exception found, skipping rule",
                            rule_id=str(rule.id),
                            file_path=snapshot.file_path,
                        )
                        continue

                    # Evaluate rule
                    evaluation_result = await self.rule_engine.evaluate_rule(
                        rule=rule,
                        content=snapshot.content or "",
                        file_path=snapshot.file_path,
                        device_metadata={"device_name": device.hostname, "tags": device.tags},
                    )

                    # Create compliance check record
                    check = ComplianceCheck(
                        rule_id=rule.id,
                        device_id=device_id,
                        snapshot_id=snapshot.id,
                        file_path=snapshot.file_path,
                        status=evaluation_result["status"],
                        compliance_score=evaluation_result.get("compliance_score"),
                        violation_details=evaluation_result.get("violation_details"),
                        violation_severity=rule.severity
                        if evaluation_result["status"] == "fail"
                        else None,
                        violation_count=evaluation_result.get("violation_count", 0),
                        execution_time_ms=0,  # Would be measured in production
                        error_message=evaluation_result.get("error_message"),
                        device_metadata={"device_name": device.hostname, "tags": device.tags},
                        file_metadata={
                            "content_hash": snapshot.content_hash,
                            "file_size": snapshot.file_size,
                            "last_modified": snapshot.created_at.isoformat(),
                        },
                        check_metadata=evaluation_result,
                    )

                    session.add(check)
                    compliance_checks.append(check)

                    # Update rule statistics
                    rule.total_checks += 1
                    if check.status == "fail":
                        rule.violation_count += 1
                        rule.last_violation_at = datetime.now(timezone.utc)
                    rule.last_checked_at = datetime.now(timezone.utc)

            await session.commit()

            logger.info(f"Completed compliance checks", checks_created=len(compliance_checks))
            return compliance_checks

        except Exception as e:
            await session.rollback()
            logger.error("Error checking device compliance", error=str(e))
            raise

    async def generate_compliance_report(
        self,
        session: AsyncSession,
        report_type: str,
        scope_id: str | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
        generated_by: str = "system",
    ) -> ComplianceReport:
        """
        Generate a comprehensive compliance report.

        Args:
            session: Database session
            report_type: Type of report (device, rule, global, category)
            scope_id: Scope identifier (device_id, rule_id, category, etc.)
            period_start: Report period start (default: 30 days ago)
            period_end: Report period end (default: now)
            generated_by: Who generated the report

        Returns:
            Generated compliance report
        """
        try:
            structlog.contextvars.bind_contextvars(
                operation="generate_compliance_report",
                report_type=report_type,
                scope_id=scope_id,
            )

            logger.info("Generating compliance report")

            # Set default time period
            if not period_end:
                period_end = datetime.now(timezone.utc)
            if not period_start:
                period_start = period_end - timedelta(days=30)

            # Build base query for compliance checks in the period
            base_query = select(ComplianceCheck).where(
                and_(
                    ComplianceCheck.checked_at >= period_start,
                    ComplianceCheck.checked_at <= period_end,
                )
            )

            # Apply scope filtering
            scope_name = "Global"
            if report_type == "device" and scope_id:
                base_query = base_query.where(ComplianceCheck.device_id == scope_id)
                device = await session.get(Device, scope_id)
                scope_name = device.hostname if device else f"Device {scope_id}"
            elif report_type == "rule" and scope_id:
                base_query = base_query.where(ComplianceCheck.rule_id == scope_id)
                rule = await session.get(ComplianceRule, scope_id)
                scope_name = rule.name if rule else f"Rule {scope_id}"
            elif report_type == "category" and scope_id:
                # Join with rules to filter by category
                base_query = base_query.join(ComplianceRule).where(
                    ComplianceRule.category == scope_id
                )
                scope_name = scope_id.title()

            # Execute query and calculate statistics
            result = await session.execute(base_query)
            checks = list(result.scalars().all())

            # Calculate compliance statistics
            total_checks = len(checks)
            passed_checks = len([c for c in checks if c.status == "pass"])
            failed_checks = len([c for c in checks if c.status == "fail"])
            error_checks = len([c for c in checks if c.status == "error"])
            skipped_checks = len([c for c in checks if c.status == "skipped"])

            # Calculate overall compliance score
            if total_checks > 0:
                overall_score = int((passed_checks / total_checks) * 100)
            else:
                overall_score = 100

            # Determine compliance grade
            if overall_score >= 95:
                grade = "A"
            elif overall_score >= 85:
                grade = "B"
            elif overall_score >= 75:
                grade = "C"
            elif overall_score >= 65:
                grade = "D"
            else:
                grade = "F"

            # Count violations by severity
            critical_violations = len([c for c in checks if c.violation_severity == "critical"])
            high_violations = len([c for c in checks if c.violation_severity == "high"])
            medium_violations = len([c for c in checks if c.violation_severity == "medium"])
            low_violations = len([c for c in checks if c.violation_severity == "low"])

            # Generate top violations summary
            violation_counts = {}
            for check in checks:
                if check.status == "fail" and check.rule:
                    rule_name = check.rule.name
                    if rule_name not in violation_counts:
                        violation_counts[rule_name] = {
                            "rule_name": rule_name,
                            "severity": check.violation_severity,
                            "count": 0,
                        }
                    violation_counts[rule_name]["count"] += 1

            top_violations = sorted(
                violation_counts.values(), key=lambda x: x["count"], reverse=True
            )[:10]

            # Create report
            report = ComplianceReport(
                report_type=report_type,
                scope_id=scope_id,
                scope_name=scope_name,
                period_start=period_start,
                period_end=period_end,
                total_checks=total_checks,
                passed_checks=passed_checks,
                failed_checks=failed_checks,
                error_checks=error_checks,
                skipped_checks=skipped_checks,
                overall_compliance_score=overall_score,
                compliance_grade=grade,
                compliance_trend="stable",  # Would calculate based on historical data
                critical_violations=critical_violations,
                high_violations=high_violations,
                medium_violations=medium_violations,
                low_violations=low_violations,
                violations_remediated=0,  # Would track remediation actions
                auto_remediations=0,
                manual_remediations=0,
                pending_remediations=failed_checks,
                top_violations=top_violations,
                improvement_recommendations=[],  # Would generate based on patterns
                compliance_trends={},  # Would include historical trend data
                generated_by=generated_by,
            )

            session.add(report)
            await session.commit()
            await session.refresh(report)

            logger.info("Compliance report generated successfully", report_id=str(report.id))
            return report

        except Exception as e:
            await session.rollback()
            logger.error("Error generating compliance report", error=str(e))
            raise

    def _device_matches_rule(self, device: Device, rule: ComplianceRule) -> bool:
        """Check if a device matches the rule's targeting criteria."""

        # If no device tags specified, rule applies to all devices
        if not rule.device_tags:
            return True

        # Check if device has any of the required tags
        device_tags = device.tags or []
        return any(tag in device_tags for tag in rule.device_tags)

    async def _get_matching_snapshots(
        self,
        session: AsyncSession,
        device_id: UUID,
        file_patterns: list[str],
    ) -> list[ConfigurationSnapshot]:
        """Get configuration snapshots matching file patterns."""

        # Get latest snapshots for the device
        query = (
            select(ConfigurationSnapshot)
            .where(ConfigurationSnapshot.device_id == device_id)
            .order_by(desc(ConfigurationSnapshot.created_at))
        )

        result = await session.execute(query)
        all_snapshots = list(result.scalars().all())

        # Filter by file patterns
        matching_snapshots = []
        for snapshot in all_snapshots:
            for pattern in file_patterns:
                if self._matches_pattern(snapshot.file_path, pattern):
                    matching_snapshots.append(snapshot)
                    break

        # Get only the latest snapshot for each file
        latest_snapshots = {}
        for snapshot in matching_snapshots:
            file_path = snapshot.file_path
            if (
                file_path not in latest_snapshots
                or snapshot.created_at > latest_snapshots[file_path].created_at
            ):
                latest_snapshots[file_path] = snapshot

        return list(latest_snapshots.values())

    def _matches_pattern(self, file_path: str, pattern: str) -> bool:
        """Check if a file path matches a pattern (supports wildcards)."""

        import fnmatch

        return fnmatch.fnmatch(file_path, pattern)

    async def _has_active_exception(
        self,
        session: AsyncSession,
        rule_id: UUID,
        device_id: UUID,
        file_path: str,
    ) -> bool:
        """Check if there's an active exception for this rule/device/file combination."""

        now = datetime.now(timezone.utc)

        query = select(ComplianceException).where(
            and_(
                ComplianceException.rule_id == rule_id,
                ComplianceException.active == True,
                ComplianceException.valid_from <= now,
                or_(
                    ComplianceException.valid_until.is_(None),
                    ComplianceException.valid_until >= now,
                ),
                or_(
                    ComplianceException.device_id.is_(None),  # Global exception
                    ComplianceException.device_id == device_id,  # Device-specific
                ),
            )
        )

        result = await session.execute(query)
        exceptions = list(result.scalars().all())

        # Check if any exception applies to this file
        for exception in exceptions:
            if not exception.file_pattern or self._matches_pattern(
                file_path, exception.file_pattern
            ):
                return True

        return False


# Singleton service instance
_compliance_service: ComplianceService | None = None


async def get_compliance_service() -> ComplianceService:
    """Get the singleton compliance service instance."""
    global _compliance_service
    if _compliance_service is None:
        _compliance_service = ComplianceService()
    return _compliance_service


async def cleanup_compliance_service() -> None:
    """Clean up the compliance service."""
    global _compliance_service
    if _compliance_service is not None:
        _compliance_service = None
        logger.info("Compliance service cleaned up")
