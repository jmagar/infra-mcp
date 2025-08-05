#!/usr/bin/env python3
"""
Test script for the Gotify notification system.

This script demonstrates the simplified notification system by:
1. Creating a test configuration change alert
2. Processing it through the notification service
3. Sending a Gotify notification with risk-based formatting
"""

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

# Add the apps/backend/src directory to Python path for imports
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps", "backend"))

from src.schemas.notification import ConfigurationChangeAlert
from src.services.notification_service import GotifyNotificationService


async def test_notification_system():
    """Test the Gotify notification system with different risk levels."""

    # Initialize the notification service
    service = GotifyNotificationService()

    # Test notification templates for different risk levels
    test_alerts = [
        ConfigurationChangeAlert(
            event_id=f"test-{uuid4().hex[:8]}",
            device_id=uuid4(),
            device_name="test-server-01",
            configuration_path="/etc/docker/daemon.json",
            change_type="file_modified",
            risk_level="low",
            previous_hash="abc123",
            current_hash="def456",
            diff_summary="Changed log driver from json-file to syslog",
            affected_services=["docker"],
            rollback_available=True,
            triggered_by="system",
            trigger_source="file_watcher",
            timestamp=datetime.now(timezone.utc),
            confidence_score=0.85,
            severity_factors=["configuration_change"],
            recommended_actions=["Verify docker containers still function properly"],
            impact_summary={"docker": "logging configuration changed"},
        ),
        ConfigurationChangeAlert(
            event_id=f"test-{uuid4().hex[:8]}",
            device_id=uuid4(),
            device_name="prod-web-02",
            configuration_path="/etc/nginx/sites-available/default",
            change_type="file_modified",
            risk_level="high",
            previous_hash="xyz789",
            current_hash="uvw012",
            diff_summary="Modified SSL configuration and added security headers",
            affected_services=["nginx", "web-app"],
            rollback_available=True,
            triggered_by="admin",
            trigger_source="manual_edit",
            timestamp=datetime.now(timezone.utc),
            confidence_score=0.92,
            severity_factors=["security_config", "production_system"],
            recommended_actions=[
                "Test SSL certificate validity",
                "Verify web application accessibility",
                "Check security header compliance",
            ],
            impact_summary={
                "nginx": "SSL configuration updated",
                "security": "Added HSTS and CSP headers",
                "performance": "Enabled HTTP/2",
            },
        ),
        ConfigurationChangeAlert(
            event_id=f"test-{uuid4().hex[:8]}",
            device_id=uuid4(),
            device_name="db-cluster-01",
            configuration_path="/etc/postgresql/postgresql.conf",
            change_type="file_modified",
            risk_level="critical",
            previous_hash="critical123",
            current_hash="critical456",
            diff_summary="Modified shared_buffers from 128MB to 4GB and changed max_connections",
            affected_services=["postgresql", "api-backend", "web-frontend"],
            rollback_available=True,
            triggered_by="dba_user",
            trigger_source="configuration_management",
            timestamp=datetime.now(timezone.utc),
            confidence_score=0.95,
            severity_factors=["database_config", "memory_allocation", "production_critical"],
            recommended_actions=[
                "Monitor database memory usage immediately",
                "Check connection pool status",
                "Verify application performance",
                "Have rollback plan ready",
            ],
            impact_summary={
                "memory": "Increased shared_buffers by 30x",
                "connections": "Modified max_connections limit",
                "performance": "Potential significant impact on database performance",
            },
        ),
    ]

    print("🔧 Testing Gotify Notification System")
    print("=" * 50)

    for i, alert in enumerate(test_alerts, 1):
        print(f"\n📋 Test {i}: {alert.risk_level.upper()} Risk Alert")
        print(f"Device: {alert.device_name}")
        print(f"File: {alert.configuration_path}")
        print(f"Risk Level: {alert.risk_level}")

        # Render the notification content
        title, message = await service._render_notification_content(alert)

        print(f"\n📨 Generated Notification:")
        print(f"Title: {title}")
        print(f"Message:\n{message}")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(test_notification_system())
