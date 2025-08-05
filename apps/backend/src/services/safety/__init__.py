"""
Safety Services Package

Multi-layered destructive action protection system providing:
- Command pattern detection and analysis
- Risk assessment with device-specific context
- Multi-step confirmation workflows
- Audit trails and recovery procedures
"""

from .destructive_action_detector import DestructiveActionDetector, DestructiveActionType
from .risk_assessment_engine import RiskAssessmentEngine, RiskLevel
from .patterns import DESTRUCTIVE_COMMAND_PATTERNS
from .rules import DEVICE_PROTECTION_RULES

from .action_manager import DestructiveActionManager, OperationStatus

__all__ = [
    "DestructiveActionDetector",
    "DestructiveActionType",
    "RiskAssessmentEngine",
    "RiskLevel",
    "DestructiveActionManager",
    "OperationStatus",
    "DESTRUCTIVE_COMMAND_PATTERNS",
    "DEVICE_PROTECTION_RULES",
]
