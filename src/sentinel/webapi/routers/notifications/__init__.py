"""
Notification and system management API routers.

This module provides modular notification and system API endpoints organized by functionality:
- send: Notification sending and delivery
- channels: Channel testing and status monitoring
- system: System health checks and information
- maintenance: System cleanup and maintenance tasks
"""

from fastapi import APIRouter

from . import channels, maintenance, send, system

# Create main notifications router
router = APIRouter()

# Include all sub-routers with appropriate prefixes and tags

# Notification sending: /notifications/send
router.include_router(send.router, prefix="/notifications", tags=["Notifications"])

# Channel management: /notifications/test, /notifications/channels/status
router.include_router(
    channels.router, prefix="/notifications/channels", tags=["Notification Channels"]
)

# System endpoints: /system/health, /system/info
router.include_router(system.router, prefix="/system", tags=["System Management"])

# Maintenance endpoints: /system/maintenance/cleanup
router.include_router(
    maintenance.router, prefix="/system/maintenance", tags=["System Maintenance"]
)

__all__ = ["router"]
