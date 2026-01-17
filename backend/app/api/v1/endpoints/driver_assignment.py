"""
Driver Assignment API Endpoints - Phase 2.4.2.

Fleet Owners assign drivers to PLANNED trips with connectivity validation.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.db.session import get_db
from backend.app.models.trip import Trip
from backend.app.models.trip_stop import TripStop
from backend.app.models.user import User
from backend.app.models.trip_enums import TripStatus
from backend.app.models.enums import UserRole
from backend.app.schemas.driver_assignment import DriverAssignment, DriverAssignmentResponse
from backend.app.schemas.trip import TripResponse, TripStopResponse, TripListResponse
from backend.app.core.guards import require_role, OwnershipGuard
from backend.app.services.audit import log_event, AuditAction
from backend.app.services.route_connectivity import can_assign_driver_to_trip

router = APIRouter(prefix="/fleet-owner", tags=["Fleet Owner - Driver Assignment"])
ownership_guard = OwnershipGuard()


@router.patch("/trips/{trip_id}/assign-driver")
async def assign_driver_to_trip(
    trip_id: int = Path(..., description="Trip ID"),
    assignment: DriverAssignment = ...,
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign a driver to a PLANNED trip (Fleet Owner only).
    
    Validates:
    - Trip is in PLANNED status
    - Driver belongs to Fleet Owner
    - Driver is active
    - Route connectivity if driver has other PLANNED trips
    
    Changes trip status from PLANNED to PENDING after assignment.
    """
    # Get trip and validate ownership
    trip_result = await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )
    trip = trip_result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    ownership_guard.enforce(trip.fleet_owner_id, current_user, "trip")
    
    # Validate trip is PLANNED
    if trip.status != TripStatus.PLANNED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only assign driver to PLANNED trip, current status: {trip.status.value}"
        )
    
    # Get driver and validate
    driver_result = await db.execute(
        select(User).where(User.id == assignment.driver_id)
    )
    driver = driver_result.scalar_one_or_none()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Validate driver role
    if driver.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a driver"
        )
    
    # Validate driver is active
    if not driver.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver is not active"
        )
    
    # Validate driver belongs to fleet owner
    if driver.fleet_owner_id != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Driver does not belong to your fleet"
        )
    
    # Validate route connectivity
    can_assign, connectivity_reason = await can_assign_driver_to_trip(
        db=db,
        driver_id=assignment.driver_id,
        new_trip=trip
    )
    
    if not can_assign:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot assign driver: {connectivity_reason}"
        )
    
    # Assign driver
    trip.driver_id = assignment.driver_id
    trip.status = TripStatus.PENDING  # Move from PLANNED to PENDING
    
    await db.commit()
    await db.refresh(trip)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.DRIVER_ASSIGNED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "trip_id": trip.id,
            "driver_id": assignment.driver_id,
            "driver_username": driver.username,
            "connectivity_validated": can_assign,
            "connectivity_reason": connectivity_reason
        }
    )
    
    return DriverAssignmentResponse(
        trip_id=trip.id,
        driver_id=trip.driver_id,
        status=trip.status.value,
        connectivity_validated=can_assign,
        connectivity_reason=connectivity_reason
    )


@router.patch("/trips/{trip_id}/unassign-driver")
async def unassign_driver_from_trip(
    trip_id: int = Path(..., description="Trip ID"),
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Unassign driver from a trip (Fleet Owner only).
    
    Moves trip back to PLANNED status.
    Only allowed for PENDING trips (not started).
    """
    # Get trip and validate ownership
    trip_result = await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )
    trip = trip_result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    ownership_guard.enforce(trip.fleet_owner_id, current_user, "trip")
    
    # Validate trip is PENDING (not started)
    if trip.status != TripStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only unassign driver from PENDING trip, current status: {trip.status.value}"
        )
    
    if not trip.driver_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No driver assigned to this trip"
        )
    
    old_driver_id = trip.driver_id
    
    # Unassign driver
    trip.driver_id = None
    trip.status = TripStatus.PLANNED  # Move back to PLANNED
    
    await db.commit()
    await db.refresh(trip)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.DRIVER_UNASSIGNED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "trip_id": trip.id,
            "previous_driver_id": old_driver_id
        }
    )
    
    return {
        "trip_id": trip.id,
        "status": trip.status.value,
        "driver_unassigned": True
    }
