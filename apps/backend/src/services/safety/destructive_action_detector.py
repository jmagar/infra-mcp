"""
Destructive Action Detector

Primary entry point for the safety system that analyzes command strings
to detect potentially destructive operations before they are executed.
"""

import re
import logging
from typing import Any

from .patterns import DestructiveActionType, DESTRUCTIVE_COMMAND_PATTERNS
from .risk_assessment_engine import RiskAssessmentEngine

logger = logging.getLogger(__name__)


class DestructiveActionDetector:
    """
    Analyzes commands to detect potentially destructive operations.

    Features:
    - Pattern-based command analysis using regex
    - Integration with risk assessment engine
    - Context-aware evaluation based on device type
    - Support for 25+ destructive action types
    - Configurable sensitivity levels
    """

    def __init__(self, risk_assessment_engine: RiskAssessmentEngine | None = None):
        """
        Initialize the destructive action detector.

        Args:
            risk_assessment_engine: Engine for evaluating risk levels
        """
        self.risk_assessment_engine = risk_assessment_engine or RiskAssessmentEngine()
        self.patterns = DESTRUCTIVE_COMMAND_PATTERNS

        # Compile regex patterns for performance
        self._compiled_patterns: dict[DestructiveActionType, list[re.Pattern[str]]] = {}
        self._compile_patterns()

        logger.info(
            f"DestructiveActionDetector initialized with {len(self.patterns)} action types "
            f"and {sum(len(patterns) for patterns in self.patterns.values())} total patterns"
        )

    def _compile_patterns(self) -> None:
        """Compile regex patterns for better performance."""
        for action_type, patterns in self.patterns.items():
            compiled_patterns = []
            for pattern in patterns:
                try:
                    compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.warning(f"Invalid regex pattern for {action_type}: {pattern} - {e}")
                    continue
            self._compiled_patterns[action_type] = compiled_patterns

    async def analyze_command(
        self,
        command: str,
        device_context: dict[str, Any],
        user_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Analyze a command and return risk analysis if destructive.

        Args:
            command: The command string to analyze
            device_context: Rich context about the target device including:
                - device_id: UUID of the device
                - hostname: Device hostname
                - os_type: Operating system type (ubuntu, unraid, wsl2, etc.)
                - environment: Environment type (production, development, etc.)
                - running_container_count: Number of running containers
                - available_services: List of available services
                - current_user: Current user context
            user_context: Optional user context for auditing

        Returns:
            Dictionary containing full analysis and confirmation requirements,
            or None if the command is deemed safe
        """
        if not command or not command.strip():
            return None

        # Normalize command for analysis
        normalized_command = command.strip()

        # Check each action type for pattern matches
        for action_type, compiled_patterns in self._compiled_patterns.items():
            for pattern in compiled_patterns:
                match = pattern.search(normalized_command)
                if match:
                    logger.info(
                        f"Destructive pattern detected: {action_type.value} in command: "
                        f"{normalized_command[:100]}..."
                    )

                    # Perform detailed risk analysis
                    analysis = await self.risk_assessment_engine.assess(
                        action_type=action_type,
                        command=normalized_command,
                        device_context=device_context,
                        matched_pattern=pattern.pattern,
                        match_details={
                            "matched_text": match.group(0),
                            "match_start": match.start(),
                            "match_end": match.end(),
                        },
                    )

                    # Add detector metadata
                    analysis.update(
                        {
                            "detector_info": {
                                "matched_pattern": pattern.pattern,
                                "action_type": action_type.value,
                                "detection_timestamp": device_context.get("timestamp"),
                                "analyzer_version": "1.0.0",
                            },
                            "original_command": command,
                            "normalized_command": normalized_command,
                        }
                    )

                    # Only return analysis if confirmation is required
                    if analysis.get("requires_confirmation", False):
                        logger.warning(
                            f"Blocking destructive action {action_type.value} on device "
                            f"{device_context.get('hostname', 'unknown')} - "
                            f"Risk level: {analysis.get('risk_level', 'UNKNOWN')}"
                        )
                        return analysis
                    else:
                        logger.info(
                            f"Destructive action {action_type.value} detected but risk level "
                            f"{analysis.get('risk_level', 'UNKNOWN')} does not require confirmation"
                        )
                        return None

        # No destructive patterns detected
        logger.debug(f"Command analyzed - no destructive patterns detected: {normalized_command}")
        return None

    def get_supported_action_types(self) -> list[DestructiveActionType]:
        """Get list of all supported destructive action types."""
        return list(self._compiled_patterns.keys())

    def get_patterns_for_action_type(self, action_type: DestructiveActionType) -> list[str]:
        """Get original string patterns for a specific action type."""
        return self.patterns.get(action_type, [])

    def test_pattern_match(
        self, command: str, action_type: DestructiveActionType | None = None
    ) -> dict[str, Any]:
        """
        Test if a command matches any patterns (for debugging/testing).

        Args:
            command: Command to test
            action_type: Specific action type to test against (optional)

        Returns:
            Dictionary with match information
        """
        results = {
            "command": command,
            "matches": [],
            "total_matches": 0,
        }

        patterns_to_check = {}
        if action_type and action_type in self._compiled_patterns:
            patterns_to_check[action_type] = self._compiled_patterns[action_type]
        else:
            patterns_to_check = self._compiled_patterns

        for act_type, compiled_patterns in patterns_to_check.items():
            for i, pattern in enumerate(compiled_patterns):
                match = pattern.search(command)
                if match:
                    results["matches"].append(
                        {
                            "action_type": act_type.value,
                            "pattern_index": i,
                            "pattern": pattern.pattern,
                            "matched_text": match.group(0),
                            "match_start": match.start(),
                            "match_end": match.end(),
                        }
                    )
                    results["total_matches"] += 1

        return results

    def add_custom_pattern(self, action_type: DestructiveActionType, pattern: str) -> bool:
        """
        Add a custom pattern for an action type.

        Args:
            action_type: Action type to add pattern for
            pattern: Regular expression pattern

        Returns:
            True if pattern was added successfully
        """
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)

            if action_type not in self.patterns:
                self.patterns[action_type] = []
                self._compiled_patterns[action_type] = []

            self.patterns[action_type].append(pattern)
            self._compiled_patterns[action_type].append(compiled_pattern)

            logger.info(f"Added custom pattern for {action_type.value}: {pattern}")
            return True

        except re.error as e:
            logger.error(f"Failed to add custom pattern {pattern} for {action_type.value}: {e}")
            return False

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about loaded patterns."""
        return {
            "total_action_types": len(self._compiled_patterns),
            "total_patterns": sum(len(patterns) for patterns in self._compiled_patterns.values()),
            "patterns_by_type": {
                action_type.value: len(patterns)
                for action_type, patterns in self._compiled_patterns.items()
            },
            "largest_pattern_group": max(
                (action_type.value, len(patterns))
                for action_type, patterns in self._compiled_patterns.items()
            )
            if self._compiled_patterns
            else ("none", 0),
        }
