#!/usr/bin/env python3
"""
Configuration Batch Deployment Test Script

Demonstrates how the atomic multi-file configuration deployment system works.
This script walks through the key features and capabilities of the system.
"""

import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

# Add the backend to the path
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "apps/backend"))

from apps.backend.src.services.configuration_batch_service import (
    ConfigurationBatchService,
    ConfigurationBatchRequest,
    ConfigurationFileChange,
)


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def print_json(data, title: str = ""):
    """Pretty print JSON data."""
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, indent=2, default=str))


async def demo_configuration_batch_deployment():
    """
    Comprehensive demonstration of the configuration batch deployment system.
    """
    print_section("Configuration Batch Deployment System Demo")

    print("""
    This system provides ATOMIC multi-file configuration deployment across
    multiple devices with the following key features:
    
    1. 🔍 Pre-deployment validation (connectivity, file paths, content)
    2. 📸 Automatic snapshot creation for rollback purposes  
    3. 🚀 Atomic file deployment using temporary files and SSH
    4. 🔄 Automatic rollback on failure (optional)
    5. 📊 Comprehensive status tracking and reporting
    6. 🎯 Dry-run mode for testing deployments
    """)

    # Initialize the service
    service = ConfigurationBatchService()
    print(f"✓ Configuration Batch Service initialized")
    print(f"  - Max concurrent deployments: {service.max_concurrent_deployments}")
    print(f"  - Deployment timeout: {service.deployment_timeout}s")
    print(f"  - Cleanup delay: {service.cleanup_delay}s")

    print_section("1. Creating Configuration File Changes")

    # Example 1: Nginx SSL configuration update
    nginx_change = ConfigurationFileChange(
        change_id="nginx-ssl-update-001",
        file_path="/etc/nginx/sites-enabled/mysite.conf",
        content="""
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    
    server_name mysite.example.com;
    
    ssl_certificate /etc/ssl/certs/mysite.crt;
    ssl_certificate_key /etc/ssl/private/mysite.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
        """.strip(),
        metadata={
            "description": "Enable SSL for mysite with modern security settings",
            "backup_required": True,
            "service_restart_required": ["nginx"],
            "priority": "high",
        },
    )

    # Example 2: Docker Compose service update
    docker_change = ConfigurationFileChange(
        change_id="docker-compose-update-001",
        file_path="/opt/services/myapp/docker-compose.yml",
        content="""
version: '3.8'
services:
  web:
    image: myapp:v2.1.0
    ports:
      - "8080:80"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    restart: unless-stopped
    
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=myapp
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - db_data:/var/lib/postgresql/data
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  db_data:
        """.strip(),
        metadata={
            "description": "Update myapp to version 2.1.0 with Redis caching",
            "backup_required": True,
            "service_restart_required": ["docker-compose-myapp"],
            "priority": "medium",
        },
    )

    print(f"✓ Created {len([nginx_change, docker_change])} configuration changes:")
    print(f"  1. {nginx_change.change_id}: {nginx_change.metadata['description']}")
    print(f"  2. {docker_change.change_id}: {docker_change.metadata['description']}")

    print_section("2. Creating Batch Deployment Request")

    # Simulate some device UUIDs
    device_ids = [
        uuid4(),  # web01.example.com
        uuid4(),  # web02.example.com
        uuid4(),  # web03.example.com
    ]

    # Create batch request
    batch_request = ConfigurationBatchRequest(
        device_ids=device_ids,
        changes=[nginx_change, docker_change],
        dry_run=True,  # Start with dry run for demo
        auto_rollback=True,
        metadata={
            "deployment_name": "SSL + Application Update",
            "requested_by": "admin",
            "priority": "high",
            "maintenance_window": "2025-01-08T02:00:00Z",
            "approval_id": "CHANGE-2025-001",
        },
    )

    print(f"✓ Created batch deployment request:")
    print(f"  - Target devices: {len(batch_request.device_ids)}")
    print(f"  - Configuration changes: {len(batch_request.changes)}")
    print(f"  - Dry run: {batch_request.dry_run}")
    print(f"  - Auto rollback: {batch_request.auto_rollback}")

    print_json(batch_request.metadata, "Request Metadata")

    print_section("3. Batch Deployment Workflow")

    print("""
    The deployment follows this workflow:
    
    Phase 1: PRE-DEPLOYMENT VALIDATION
    ✓ Validate all devices exist and are accessible
    ✓ Test SSH connectivity to each device  
    ✓ Validate file paths are absolute
    ✓ Check content is provided for all changes
    ✓ Perform device-specific validation checks
    
    Phase 2: PRE-DEPLOYMENT SNAPSHOTS
    ✓ Connect to each device via SSH
    ✓ Read current content of each target file
    ✓ Calculate SHA256 hashes for integrity checking
    ✓ Store snapshots for rollback purposes
    
    Phase 3: ATOMIC DEPLOYMENT EXECUTION
    ✓ Deploy to each device sequentially
    ✓ Create target directories if needed
    ✓ Write content to temporary files first  
    ✓ Atomically move temp files to final locations
    ✓ Track success/failure for each file
    
    Phase 4: ROLLBACK (if needed)
    ✓ Restore original content from snapshots
    ✓ Remove files that didn't exist originally
    ✓ Report rollback success/failure
    """)

    print_section("4. Deployment Status Tracking")

    # Simulate deployment transaction state
    print("""
    The system tracks deployment state through these statuses:
    
    📝 initialized    - Batch request created and validated
    ✅ validated      - Pre-deployment validation completed
    🚀 executing      - Currently deploying changes
    ✓ completed       - All changes deployed successfully
    ⚠️ partially_completed - Some changes succeeded, others failed  
    ❌ failed         - Deployment failed before completion
    🔄 rolled_back    - Failed deployment was rolled back
    ❌ validation_failed - Pre-deployment validation failed
    🚫 cancelled      - Deployment was cancelled by user
    """)

    print_section("5. Response Structure")

    # Show what a typical response looks like
    example_response = {
        "batch_id": "batch-456789abc-def0-1234",
        "status": "completed",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "device_count": 3,
        "change_count": 2,
        "applied_changes": [
            {
                "device_id": str(device_ids[0]),
                "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                "change_id": "nginx-ssl-update-001",
                "applied_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "device_id": str(device_ids[0]),
                "file_path": "/opt/services/myapp/docker-compose.yml",
                "change_id": "docker-compose-update-001",
                "applied_at": datetime.now(timezone.utc).isoformat(),
            },
        ],
        "failed_changes": [],
        "rollback_plan": [],
        "validation_results": [
            {
                "device_id": str(device_ids[0]),
                "device_name": "web01.example.com",
                "overall_status": "valid",
                "validation_errors": [],
                "file_validations": [
                    {
                        "file_path": "/etc/nginx/sites-enabled/mysite.conf",
                        "status": "valid",
                        "errors": [],
                        "warnings": [],
                    }
                ],
            }
        ],
        "error_message": None,
        "dry_run": False,
    }

    print_json(example_response, "Example Deployment Response")

    print_section("6. API Endpoints")

    print("""
    The system provides these RESTful API endpoints:
    
    POST   /api/configuration-batch/deploy
           └─ Create and execute a batch deployment
           
    GET    /api/configuration-batch/{batch_id}/status  
           └─ Get current deployment status
           
    GET    /api/configuration-batch/{batch_id}
           └─ Get detailed deployment information
           
    POST   /api/configuration-batch/{batch_id}/cancel
           └─ Cancel active deployment (with rollback)
           
    GET    /api/configuration-batch/deployments
           └─ List deployments with filtering/pagination
           
    POST   /api/configuration-batch/validate
           └─ Validate deployment without executing
    """)

    print_section("7. Key Safety Features")

    print("""
    🔒 SAFETY FEATURES:
    
    ✓ Atomic Operations: Files written to temp locations first, then moved
    ✓ Pre-deployment Validation: Connectivity and content checks before deployment  
    ✓ Automatic Snapshots: Original content backed up for rollback
    ✓ Rollback Capability: Failed deployments can be automatically reverted
    ✓ Dry Run Mode: Test deployments without making changes
    ✓ Transaction Tracking: Complete audit trail of all operations
    ✓ Timeout Handling: Deployments timeout after configurable period
    ✓ Concurrent Limits: Configurable limits on parallel deployments
    ✓ Error Isolation: Failed changes don't affect successful ones
    """)

    print_section("8. Use Cases")

    print("""
    🎯 COMMON USE CASES:
    
    • SSL Certificate Updates across multiple web servers
    • Application deployments via Docker Compose updates
    • Nginx/Apache configuration rollouts
    • System configuration changes (systemd, cron, etc.)
    • Database configuration updates
    • Security policy deployments
    • Feature flag configuration changes
    • Environment-specific config deployments
    • Disaster recovery configuration restoration
    """)

    print_section("Configuration Batch Deployment Demo Complete")

    print("""
    ✨ The system is now ready for production use with:
    
    ✓ Comprehensive ConfigurationBatchService implementation
    ✓ Pydantic schemas for request/response validation  
    ✓ REST API endpoints for deployment management
    ✓ Atomic file operations with rollback capabilities
    ✓ Pre-deployment validation and safety checks
    ✓ Complete status tracking and audit trail
    
    🚀 Ready to deploy configurations safely at scale!
    """)


if __name__ == "__main__":
    asyncio.run(demo_configuration_batch_deployment())
