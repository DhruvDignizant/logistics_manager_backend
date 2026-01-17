"""
Admin API Endpoints.

Provides admin-only user management endpoints with audit logging.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.models.audit_log import AuditLog
from backend.app.schemas.admin import (
    UserListResponse, UserListItem, BlockUserRequest, UnblockUserRequest,
    AdminActionResponse, AuditTrailResponse, AuditLogResponse
)
from backend.app.core.guards import require_admin
from backend.app.core.token_revocation import revoke_all_user_tokens, clear_user_token_revocation
from backend.app.services.audit import log_admin_action, AuditAction, get_audit_trail

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all users in the system (admin-only).
    
    Returns paginated user list with role and status information.
    """
    # Get total count
    count_query = select(func.count(User.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated users
    offset = (page - 1) * page_size
    query = select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return UserListResponse(
        users=[UserListItem.model_validate(user) for user in users],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/users/{user_id}", response_model=UserListItem)
async def get_user(
    user_id: int,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific user (admin-only).
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserListItem.model_validate(user)


@router.post("/users/{user_id}/block", response_model=AdminActionResponse)
async def block_user(
    user_id: int,
    request: BlockUserRequest,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Block a user and revoke all their active tokens (admin-only).
    
    This immediately terminates all user sessions.
    """
    # Get target user
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent blocking another admin
    if target_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot block another admin user"
        )
    
    # Prevent blocking self
    if target_user.id == admin["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot block yourself"
        )
    
    # Check if already blocked
    if not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already blocked"
        )
    
    # Block the user
    target_user.is_active = False
    await db.commit()
    
    # Revoke all active tokens
    await revoke_all_user_tokens(user_id)
    
    # Log the action
    audit_log = await log_admin_action(
        db=db,
        admin_id=admin["user_id"],
        admin_username=admin["sub"],
        action=AuditAction.USER_BLOCKED,
        target_user_id=target_user.id,
        target_username=target_user.username,
        metadata={"reason": request.reason} if request.reason else None
    )
    
    return AdminActionResponse(
        success=True,
        message=f"User '{target_user.username}' has been blocked",
        user_id=user_id,
        action=AuditAction.USER_BLOCKED,
        audit_log_id=audit_log.id
    )


@router.post("/users/{user_id}/unblock", response_model=AdminActionResponse)
async def unblock_user(
    user_id: int,
    request: UnblockUserRequest,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Unblock a user and clear token revocations (admin-only).
    
    User will be able to login again and generate new tokens.
    """
    # Get target user
    result = await db.execute(select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if already active
    if target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already active"
        )
    
    # Unblock the user
    target_user.is_active = True
    await db.commit()
    
    # Clear token revocations (user can now login and get new tokens)
    await clear_user_token_revocation(user_id)
    
    # Log the action
    audit_log = await log_admin_action(
        db=db,
        admin_id=admin["user_id"],
        admin_username=admin["sub"],
        action=AuditAction.USER_UNBLOCKED,
        target_user_id=target_user.id,
        target_username=target_user.username,
        metadata={"reason": request.reason} if request.reason else None
    )
    
    return AdminActionResponse(
        success=True,
        message=f"User '{target_user.username}' has been unblocked",
        user_id=user_id,
        action=AuditAction.USER_UNBLOCKED,
        audit_log_id=audit_log.id
    )


@router.get("/audit-logs", response_model=AuditTrailResponse)
async def get_audit_logs(
    user_id: int = Query(None, description="Filter by target user ID"),
    action: str = Query(None, description="Filter by action type"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit trail with optional filtering (admin-only).
    
    Returns recent audit logs for security monitoring and compliance.
    """
    logs = await get_audit_trail(
        db=db,
        target_user_id=user_id,
        action=action,
        limit=limit
    )
    
    return AuditTrailResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs)
    )


@router.get("/users/{user_id}/audit-history", response_model=AuditTrailResponse)
async def get_user_audit_history(
    user_id: int,
    limit: int = Query(50, ge=1, le=500),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete audit history for a specific user (admin-only).
    
    Shows all actions performed by or on the user.
    """
    from backend.app.services.audit import get_user_audit_history as get_history
    
    logs = await get_history(db=db, user_id=user_id, limit=limit)
    
    return AuditTrailResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=len(logs)
    )


# Phase 2.1 - Hub Management (Admin read-only)
@router.get("/hubs")
async def list_all_hubs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all hubs in the system (admin read-only).
    
    Returns all hubs from all Hub Owners for monitoring purposes.
    """
    from backend.app.models.hub import Hub
    from backend.app.schemas.hub import HubResponse, HubListResponse
    
    # Get total count (all hubs, including inactive for admin)
    count_query = select(func.count(Hub.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated hubs
    offset = (page - 1) * page_size
    query = select(Hub).order_by(Hub.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    hubs = result.scalars().all()
    
    return HubListResponse(
        hubs=[HubResponse.model_validate(hub) for hub in hubs],
        total=total,
        page=page,
        page_size=page_size
    )


# Phase 2.2 - Parcel Management (Admin read-only)
@router.get("/parcels")
async def list_all_parcels(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all parcels in the system (admin read-only).
    
    Returns all parcels from all Hub Owners for monitoring purposes.
    """
    from backend.app.models.parcel import Parcel
    from backend.app.schemas.parcel import ParcelResponse, ParcelListResponse
    
    # Get total count (all parcels, including inactive for admin)
    count_query = select(func.count(Parcel.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated parcels
    offset = (page - 1) * page_size
    query = select(Parcel).order_by(Parcel.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    parcels = result.scalars().all()
    
    return ParcelListResponse(
        parcels=[ParcelResponse.model_validate(parcel) for parcel in parcels],
        total=total,
        page=page,
        page_size=page_size
    )


# Phase 2.3.1 - Fleet Route Management (Admin read-only)
@router.get("/routes")
async def list_all_routes(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all fleet routes in the system (admin read-only).
    
    Returns all routes from all Fleet Owners for monitoring purposes.
    """
    from backend.app.models.fleet_route import FleetRoute
    from backend.app.schemas.fleet_route import FleetRouteResponse, FleetRouteListResponse
    
    # Get total count (all routes, including inactive for admin)
    count_query = select(func.count(FleetRoute.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated routes
    offset = (page - 1) * page_size
    query = select(FleetRoute).order_by(FleetRoute.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    routes = result.scalars().all()
    
    return FleetRouteListResponse(
        routes=[FleetRouteResponse.model_validate(route) for route in routes],
        total=total,
        page=page,
        page_size=page_size
    )


# Phase 2.3.1a - Fleet Vehicle Management (Admin read-only)
@router.get("/vehicles")
async def list_all_vehicles(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List all fleet vehicles in the system (admin read-only).
    
    Returns all vehicles from all Fleet Owners for monitoring purposes.
    """
    from backend.app.models.fleet_vehicle import FleetVehicle
    from backend.app.schemas.fleet_vehicle import FleetVehicleResponse, FleetVehicleListResponse
    
    # Get total count (all vehicles, including inactive for admin)
    count_query = select(func.count(FleetVehicle.id))
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated vehicles
    offset = (page - 1) * page_size
    query = select(FleetVehicle).order_by(FleetVehicle.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    vehicles = result.scalars().all()
    
    return FleetVehicleListResponse(
        vehicles=[FleetVehicleResponse.model_validate(vehicle) for vehicle in vehicles],
        total=total,
        page=page,
        page_size=page_size
    )


