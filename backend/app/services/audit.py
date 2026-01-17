"""
Audit logging service for tracking security events and admin actions.

Provides centralized logging for compliance and security monitoring.
"""

from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.app.models.audit_log import AuditLog
from datetime import datetime


# Audit event constants
class AuditAction:
    """Standardized audit action constants."""
    USER_BLOCKED = "USER_BLOCKED"
    USER_UNBLOCKED = "USER_UNBLOCKED"
    USER_CREATED = "USER_CREATED"
    USER_DELETED = "USER_DELETED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    ROLE_CHANGED = "ROLE_CHANGED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    
    # Phase 2.1 - Hub Management
    HUB_CREATED = "HUB_CREATED"
    HUB_UPDATED = "HUB_UPDATED"
    HUB_DEACTIVATED = "HUB_DEACTIVATED"
    
    # Phase 2.2 - Parcel Management
    PARCEL_CREATED = "PARCEL_CREATED"
    PARCEL_UPDATED = "PARCEL_UPDATED"
    PARCEL_CANCELLED = "PARCEL_CANCELLED"
    
    # Phase 2.3.1 - Fleet Route Management
    ROUTE_CREATED = "ROUTE_CREATED"
    ROUTE_UPDATED = "ROUTE_UPDATED"
    ROUTE_DEACTIVATED = "ROUTE_DEACTIVATED"
    
    # Phase 2.3.1a - Fleet Vehicle Management
    VEHICLE_CREATED = "VEHICLE_CREATED"
    VEHICLE_UPDATED = "VEHICLE_UPDATED"
    VEHICLE_DEACTIVATED = "VEHICLE_DEACTIVATED"
    
    # Phase 2.3.2 - Route Discovery
    ROUTE_MATCH_SUGGESTED = "ROUTE_MATCH_SUGGESTED"
    HUB_ROUTE_REQUESTED = "HUB_ROUTE_REQUESTED"
    
    # Phase 2.3.3 - Route Request Decisions
    HUB_ROUTE_ACCEPTED = "HUB_ROUTE_ACCEPTED"
    HUB_ROUTE_REJECTED = "HUB_ROUTE_REJECTED"
    
    # Phase 2.4 - Trip Creation
    TRIP_CREATED = "TRIP_CREATED"
    DRIVER_ASSIGNED = "DRIVER_ASSIGNED"
    DRIVER_UNASSIGNED = "DRIVER_UNASSIGNED"
    
    # Phase 2.5 - Live Trip Execution
    TRIP_STARTED = "TRIP_STARTED"
    LOCATION_RECORDED = "LOCATION_RECORDED"
    STOP_COMPLETED = "STOP_COMPLETED"
    TRIP_COMPLETED = "TRIP_COMPLETED"
    
    # Phase 2.6 - Payments & Settlements
    TRIP_CHARGE_CALCULATED = "TRIP_CHARGE_CALCULATED"
    SETTLEMENT_CREATED = "SETTLEMENT_CREATED"
    SETTLEMENT_APPROVED = "SETTLEMENT_APPROVED"
    SETTLEMENT_PAID = "SETTLEMENT_PAID"
    PRICING_RULE_CREATED = "PRICING_RULE_CREATED"
    PRICING_RULE_DEACTIVATED = "PRICING_RULE_DEACTIVATED"


async def log_event(
    db: AsyncSession,
    action: str,
    actor_id: Optional[int] = None,
    actor_username: Optional[str] = None,
    target_user_id: Optional[int] = None,
    target_username: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None
) -> AuditLog:
    """
    Log a security or admin event to the audit log.
    
    Args:
        db: Database session
        action: Action being performed (use AuditAction constants)
        actor_id: ID of user performing the action
        actor_username: Username of actor
        target_user_id: ID of user being acted upon (if applicable)
        target_username: Username of target
        metadata: Additional context as JSON
        ip_address: IP address of the request
        
    Returns:
        Created AuditLog instance
    """
    audit_log = AuditLog(
        actor_id=actor_id,
        actor_username=actor_username,
        action=action,
        target_user_id=target_user_id,
        target_username=target_username,
        meta_data=metadata,
        ip_address=ip_address
    )
    
    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)
    
    return audit_log


async def log_admin_action(
    db: AsyncSession,
    admin_id: int,
    admin_username: str,
    action: str,
    target_user_id: int,
    target_username: str,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Log an admin action (block, unblock, delete, etc.).
    
    Args:
        db: Database session
        admin_id: ID of admin user
        admin_username: Username of admin
        action: Action performed (use AuditAction constants)
        target_user_id: ID of user being acted upon
        target_username: Username of target
        metadata: Additional context
        
    Returns:
        Created AuditLog instance
    """
    return await log_event(
        db=db,
        action=action,
        actor_id=admin_id,
        actor_username=admin_username,
        target_user_id=target_user_id,
        target_username=target_username,
        metadata=metadata
    )


async def log_auth_event(
    db: AsyncSession,
    action: str,
    user_id: Optional[int],
    username: Optional[str],
    ip_address: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Log an authentication event (login success/failure).
    
    Args:
        db: Database session
        action: AuditAction.LOGIN_SUCCESS or AuditAction.LOGIN_FAILED
        user_id: ID of user attempting login
        username: Username attempting login
        ip_address: IP address of login attempt
        metadata: Additional context (e.g., failure reason)
        
    Returns:
        Created AuditLog instance
    """
    return await log_event(
        db=db,
        action=action,
        actor_id=user_id,
        actor_username=username,
        ip_address=ip_address,
        metadata=metadata
    )


async def get_audit_trail(
    db: AsyncSession,
    target_user_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 100
) -> list[AuditLog]:
    """
    Retrieve audit trail with optional filtering.
    
    Args:
        db: Database session
        target_user_id: Filter by target user ID
        action: Filter by action type
        limit: Maximum number of records to return
        
    Returns:
        List of AuditLog instances, most recent first
    """
    query = select(AuditLog).order_by(desc(AuditLog.timestamp))
    
    if target_user_id:
        query = query.where(AuditLog.target_user_id == target_user_id)
    
    if action:
        query = query.where(AuditLog.action == action)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_user_audit_history(
    db: AsyncSession,
    user_id: int,
    limit: int = 50
) -> list[AuditLog]:
    """
    Get complete audit history for a specific user.
    
    Args:
        db: Database session
        user_id: User ID to get history for
        limit: Maximum number of records
        
    Returns:
        List of audit logs where user was actor or target
    """
    query = select(AuditLog).where(
        (AuditLog.actor_id == user_id) | (AuditLog.target_user_id == user_id)
    ).order_by(desc(AuditLog.timestamp)).limit(limit)
    
    result = await db.execute(query)
    return result.scalars().all()
