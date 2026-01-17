"""
Admin API Schema Definitions.

Pydantic schemas for admin endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from backend.app.models.enums import UserRole


class UserListItem(BaseModel):
    """Schema for user in list response."""
    id: int
    username: str
    email: str
    role: UserRole
    fleet_owner_id: Optional[int] = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for list users response."""
    users: List[UserListItem]
    total: int
    page: int
    page_size: int


class BlockUserRequest(BaseModel):
    """Schema for blocking a user."""
    reason: Optional[str] = Field(None, description="Reason for blocking (for audit log)")


class UnblockUserRequest(BaseModel):
    """Schema for unblocking a user."""
    reason: Optional[str] = Field(None, description="Reason for unblocking (for audit log)")


class AdminActionResponse(BaseModel):
    """Schema for admin action response."""
    success: bool
    message: str
    user_id: int
    action: str
    audit_log_id: int


class AuditLogResponse(BaseModel):
    """Schema for audit log entry."""
    id: int
    actor_id: Optional[int]
    actor_username: Optional[str]
    action: str
    target_user_id: Optional[int]
    target_username: Optional[str]
    meta_data: Optional[dict]
    ip_address: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


class AuditTrailResponse(BaseModel):
    """Schema for audit trail list."""
    logs: List[AuditLogResponse]
    total: int
