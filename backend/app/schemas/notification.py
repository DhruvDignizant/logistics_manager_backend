"""
Notification Schemas - Phase 0.5 Hotfix.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from backend.app.models.notification import NotificationType


class NotificationCreate(BaseModel):
    user_id: int
    type: NotificationType
    title: str
    message: str
    metadata_payload: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    id: int
    type: NotificationType
    title: str
    message: str
    metadata_payload: Optional[Dict[str, Any]]
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class BroadcastRequest(BaseModel):
    role_filter: Optional[str] = None # 'FLEET_OWNER', 'HUB_OWNER', 'DRIVER', or None for all
    type: NotificationType = NotificationType.INFO
    title: str
    message: str
