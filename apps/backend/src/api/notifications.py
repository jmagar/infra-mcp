"""
Notification Management API Endpoints

REST API endpoints for managing Gotify notification configurations,
configuration alerts, and alert suppression rules.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from apps.backend.src.core.database import get_db_session
from apps.backend.src.core.exceptions import (
    DatabaseOperationError,
    ValidationError as CustomValidationError,
    ResourceNotFoundError,
)
from apps.backend.src.schemas.notification import (
    GotifyNotificationConfigCreate,
    GotifyNotificationConfigUpdate,
    GotifyNotificationConfigResponse,
    ConfigurationAlertResponse,
    AlertSuppressionCreate,
    AlertSuppressionUpdate,
    AlertSuppressionResponse,
    ConfigurationChangeAlert,
    NotificationTestRequest,
    NotificationTestResponse,
)
from apps.backend.src.schemas.common import OperationResult, PaginationParams
from apps.backend.src.api.common import get_current_user
from apps.backend.src.services.notification_service import GotifyNotificationService
from apps.backend.src.core.logging_config import (
    set_correlation_id,
    set_operation_context,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/configs", response_model=list[GotifyNotificationConfigResponse])
async def list_notification_configs(
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
    active_only: bool = Query(True, description="Return only active configurations"),
) -> list[GotifyNotificationConfigResponse]:
    """
    List all Gotify notification configurations.

    Returns a list of notification configurations with optional filtering
    by active status.
    """
    set_operation_context("list_notification_configs")

    try:
        # TODO: Implement actual database query
        # For now, return empty list as placeholder
        return []

    except Exception as e:
        logger.error(f"Error listing notification configs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list notification configurations")


@router.post("/configs", response_model=GotifyNotificationConfigResponse)
async def create_notification_config(
    config_data: GotifyNotificationConfigCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> GotifyNotificationConfigResponse:
    """
    Create a new Gotify notification configuration.

    Creates a new notification configuration with the provided settings
    and tests the connection to ensure it's working.
    """
    set_operation_context("create_notification_config")

    try:
        service = GotifyNotificationService()

        # Test the connection before creating
        test_success = await service.test_connection(config_data.app_token)
        if not test_success:
            raise HTTPException(
                status_code=400, detail="Failed to connect to Gotify with provided app token"
            )

        # TODO: Implement actual database creation
        # For now, return a placeholder response
        return GotifyNotificationConfigResponse(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            name=config_data.name,
            app_token=config_data.app_token[:8]
            + "..."
            + config_data.app_token[-4:],  # Masked token
            gotify_url=config_data.gotify_url,
            priority_mapping=config_data.priority_mapping,
            rate_limit_per_hour=config_data.rate_limit_per_hour,
            active=True,
            last_test_at=datetime.now(timezone.utc),
            last_test_success=True,
            last_error=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by=current_user,
            updated_by=current_user,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating notification config: {e}")
        raise HTTPException(status_code=500, detail="Failed to create notification configuration")


@router.get("/configs/{config_id}", response_model=GotifyNotificationConfigResponse)
async def get_notification_config(
    config_id: UUID = Path(..., description="Notification configuration ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> GotifyNotificationConfigResponse:
    """
    Get a specific Gotify notification configuration by ID.
    """
    set_operation_context("get_notification_config")

    try:
        # TODO: Implement actual database query
        raise HTTPException(status_code=404, detail="Notification configuration not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting notification config {config_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notification configuration")


@router.put("/configs/{config_id}", response_model=GotifyNotificationConfigResponse)
async def update_notification_config(
    config_id: UUID = Path(..., description="Notification configuration ID"),
    config_data: GotifyNotificationConfigUpdate = ...,
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> GotifyNotificationConfigResponse:
    """
    Update an existing Gotify notification configuration.
    """
    set_operation_context("update_notification_config")

    try:
        # TODO: Implement actual database update
        raise HTTPException(status_code=404, detail="Notification configuration not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification config {config_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification configuration")


@router.delete("/configs/{config_id}", response_model=OperationResult)
async def delete_notification_config(
    config_id: UUID = Path(..., description="Notification configuration ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> OperationResult:
    """
    Delete a Gotify notification configuration.
    """
    set_operation_context("delete_notification_config")

    try:
        # TODO: Implement actual database deletion
        raise HTTPException(status_code=404, detail="Notification configuration not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting notification config {config_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete notification configuration")


@router.post("/test", response_model=NotificationTestResponse)
async def test_notification(
    test_request: NotificationTestRequest,
    current_user: str = Depends(get_current_user),
) -> NotificationTestResponse:
    """
    Test a Gotify notification configuration by sending a test message.
    """
    set_operation_context("test_notification")

    try:
        service = GotifyNotificationService()

        # Test connection with the provided app token
        success = await service.test_connection(test_request.app_token)

        return NotificationTestResponse(
            success=success,
            message="Test notification sent successfully"
            if success
            else "Failed to send test notification",
            tested_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Error testing notification: {e}")
        return NotificationTestResponse(
            success=False,
            message=f"Test failed: {str(e)}",
            tested_at=datetime.now(timezone.utc),
        )


@router.get("/alerts", response_model=list[ConfigurationAlertResponse])
async def list_configuration_alerts(
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
    device_id: UUID | None = Query(None, description="Filter by device ID"),
    risk_level: str | None = Query(None, description="Filter by risk level"),
    status: str | None = Query(None, description="Filter by alert status"),
    pagination: PaginationParams = Depends(),
) -> list[ConfigurationAlertResponse]:
    """
    List configuration change alerts with optional filtering.
    """
    set_operation_context("list_configuration_alerts")

    try:
        # TODO: Implement actual database query with filtering and pagination
        return []

    except Exception as e:
        logger.error(f"Error listing configuration alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to list configuration alerts")


@router.get("/alerts/{alert_id}", response_model=ConfigurationAlertResponse)
async def get_configuration_alert(
    alert_id: UUID = Path(..., description="Configuration alert ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> ConfigurationAlertResponse:
    """
    Get a specific configuration alert by ID.
    """
    set_operation_context("get_configuration_alert")

    try:
        # TODO: Implement actual database query
        raise HTTPException(status_code=404, detail="Configuration alert not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting configuration alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve configuration alert")


@router.post("/alerts/{alert_id}/retry", response_model=OperationResult)
async def retry_failed_alert(
    alert_id: UUID = Path(..., description="Configuration alert ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> OperationResult:
    """
    Retry sending a failed configuration alert.
    """
    set_operation_context("retry_failed_alert")

    try:
        # TODO: Implement alert retry logic
        return OperationResult(
            success=False,
            message="Alert retry functionality not yet implemented",
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        logger.error(f"Error retrying alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry alert")


@router.get("/suppressions", response_model=list[AlertSuppressionResponse])
async def list_alert_suppressions(
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
    active_only: bool = Query(True, description="Return only active suppression rules"),
) -> list[AlertSuppressionResponse]:
    """
    List alert suppression rules with optional filtering.
    """
    set_operation_context("list_alert_suppressions")

    try:
        # TODO: Implement actual database query
        return []

    except Exception as e:
        logger.error(f"Error listing alert suppressions: {e}")
        raise HTTPException(status_code=500, detail="Failed to list alert suppressions")


@router.post("/suppressions", response_model=AlertSuppressionResponse)
async def create_alert_suppression(
    suppression_data: AlertSuppressionCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> AlertSuppressionResponse:
    """
    Create a new alert suppression rule.
    """
    set_operation_context("create_alert_suppression")

    try:
        # TODO: Implement actual database creation
        return AlertSuppressionResponse(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            name=suppression_data.name,
            description=suppression_data.description,
            device_id=suppression_data.device_id,
            configuration_path_pattern=suppression_data.configuration_path_pattern,
            change_type=suppression_data.change_type,
            min_risk_level=suppression_data.min_risk_level,
            suppression_window_minutes=suppression_data.suppression_window_minutes,
            max_alerts_in_window=suppression_data.max_alerts_in_window,
            active=True,
            last_triggered_at=None,
            trigger_count={},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            created_by=current_user,
            updated_by=current_user,
        )

    except Exception as e:
        logger.error(f"Error creating alert suppression: {e}")
        raise HTTPException(status_code=500, detail="Failed to create alert suppression")


@router.put("/suppressions/{suppression_id}", response_model=AlertSuppressionResponse)
async def update_alert_suppression(
    suppression_id: UUID = Path(..., description="Alert suppression ID"),
    suppression_data: AlertSuppressionUpdate = ...,
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> AlertSuppressionResponse:
    """
    Update an existing alert suppression rule.
    """
    set_operation_context("update_alert_suppression")

    try:
        # TODO: Implement actual database update
        raise HTTPException(status_code=404, detail="Alert suppression not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert suppression {suppression_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update alert suppression")


@router.delete("/suppressions/{suppression_id}", response_model=OperationResult)
async def delete_alert_suppression(
    suppression_id: UUID = Path(..., description="Alert suppression ID"),
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> OperationResult:
    """
    Delete an alert suppression rule.
    """
    set_operation_context("delete_alert_suppression")

    try:
        # TODO: Implement actual database deletion
        raise HTTPException(status_code=404, detail="Alert suppression not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert suppression {suppression_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete alert suppression")


@router.post("/send-alert", response_model=OperationResult)
async def send_configuration_alert(
    alert_data: ConfigurationChangeAlert,
    config_id: UUID = Query(..., description="Notification configuration ID to use"),
    db: AsyncSession = Depends(get_db_session),
    current_user: str = Depends(get_current_user),
) -> OperationResult:
    """
    Send a configuration change alert using the specified notification configuration.

    This endpoint is primarily for testing and manual alert sending.
    """
    set_operation_context("send_configuration_alert")

    try:
        service = GotifyNotificationService()

        # Send the alert
        result = await service.send_configuration_alert(alert_data, str(config_id))

        return OperationResult(
            success=result is not None,
            message="Alert sent successfully" if result else "Failed to send alert",
            timestamp=datetime.now(timezone.utc),
            data={"gotify_message_id": result} if result else None,
        )

    except Exception as e:
        logger.error(f"Error sending configuration alert: {e}")
        raise HTTPException(status_code=500, detail="Failed to send configuration alert")
