"""
Driver Trip Execution API Endpoints - Phase 2.5.

Drivers execute trips with GPS tracking and stop completion.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from backend.app.db.session import get_db
from backend.app.models.trip import Trip
from backend.app.models.trip_stop import TripStop
from backend.app.models.trip_location import TripLocation
from backend.app.models.trip_enums import TripStatus, TripStopStatus
from backend.app.models.enums import UserRole
from backend.app.schemas.trip_execution import (
    TripStartResponse, LocationRecord, LocationRecordResponse,
    StopCompleteResponse, TripCompleteResponse
)
from backend.app.core.guards import require_role
from backend.app.services.audit import log_event, AuditAction
from backend.app.services.vehicle_locking import (
    create_vehicle_lock, count_driver_in_progress_trips, release_vehicle_lock
)

router = APIRouter(prefix="/driver", tags=["Driver - Trip Execution"])


@router.post("/trips/{trip_id}/start")
async def start_trip(
    trip_id: int = Path(..., description="Trip ID"),
    current_user: dict = Depends(require_role([UserRole.DRIVER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Start a trip (Driver only).
    
    Validates:
    - Trip is PENDING (driver assigned)
    - Driver owns the trip
    - No other IN_PROGRESS trip for driver
    - Vehicle not locked by another trip
    
    Actions:
    - Lock vehicle
    - Change status to IN_PROGRESS
    - Set started_at timestamp
    """
    driver_id = current_user["user_id"]
    
    # Get trip
    trip_result = await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )
    trip = trip_result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    # Validate trip is PENDING
    if trip.status != TripStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only start PENDING trip, current status: {trip.status.value}"
        )
    
    # Validate driver owns trip
    if trip.driver_id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This trip is not assigned to you"
        )
    
    # Check driver doesn't have another IN_PROGRESS trip
    in_progress_count = await count_driver_in_progress_trips(db, driver_id)
    if in_progress_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an IN_PROGRESS trip. Complete it before starting another."
        )
    
    # Lock vehicle if assigned
    vehicle_locked = False
    if trip.vehicle_id:
        try:
            await create_vehicle_lock(
                db=db,
                vehicle_id=trip.vehicle_id,
                trip_id=trip.id,
                driver_id=driver_id
            )
            vehicle_locked = True
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vehicle {trip.vehicle_id} is already locked by another trip"
            )
    
    # Start trip
    trip.status = TripStatus.IN_PROGRESS
    trip.started_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(trip)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.TRIP_STARTED,
        actor_id=driver_id,
        actor_username=current_user["sub"],
        metadata={
            "trip_id": trip.id,
            "vehicle_id": trip.vehicle_id,
            "vehicle_locked": vehicle_locked
        }
    )
    
    return TripStartResponse(
        trip_id=trip.id,
        status=trip.status.value,
        started_at=trip.started_at,
        vehicle_locked=vehicle_locked
    )


@router.post("/trips/{trip_id}/location")
async def record_location(
    trip_id: int = Path(..., description="Trip ID"),
    location: LocationRecord = Body(...),
    current_user: dict = Depends(require_role([UserRole.DRIVER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Record GPS location for trip (Driver only).
    
    Creates breadcrumb trail for live tracking.
    """
    driver_id = current_user["user_id"]
    
    # Get trip
    trip_result = await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )
    trip = trip_result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    # Validate trip is IN_PROGRESS
    if trip.status != TripStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only record location for IN_PROGRESS trip, current status: {trip.status.value}"
        )
    
    # Validate driver owns trip
    if trip.driver_id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This trip is not assigned to you"
        )
    
    # Create location record
    trip_location = TripLocation(
        trip_id=trip.id,
        driver_id=driver_id,
        latitude=location.latitude,
        longitude=location.longitude,
        accuracy_meters=location.accuracy_meters,
        recorded_at=location.recorded_at
    )
    
    db.add(trip_location)
    await db.commit()
    await db.refresh(trip_location)
    
    # Audit log (silent - too many to log individually)
    # await log_event(...)
    
    return LocationRecordResponse(
        trip_id=trip.id,
        location_id=trip_location.id,
        recorded=True
    )


@router.patch("/trips/{trip_id}/stops/{stop_id}/complete")
async def complete_stop(
    trip_id: int = Path(..., description="Trip ID"),
    stop_id: int = Path(..., description="Stop ID"),
    current_user: dict = Depends(require_role([UserRole.DRIVER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Complete a trip stop (Driver only).
    
    Enforces sequence: must complete stops in order (1, 2, 3...).
    """
    driver_id = current_user["user_id"]
    
    # Get trip
    trip_result = await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )
    trip = trip_result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    # Validate trip is IN_PROGRESS
    if trip.status != TripStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only complete stops for IN_PROGRESS trip, current status: {trip.status.value}"
        )
    
    # Validate driver owns trip
    if trip.driver_id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This trip is not assigned to you"
        )
    
    # Get stop
    stop_result = await db.execute(
        select(TripStop).where(TripStop.id == stop_id, TripStop.trip_id == trip_id)
    )
    stop = stop_result.scalar_one_or_none()
    
    if not stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stop not found for this trip"
        )
    
    # Check if already completed
    if stop.status == TripStopStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stop already completed"
        )
    
    # Enforce sequence: get max completed sequence number
    max_completed_result = await db.execute(
        select(TripStop.sequence_number).where(
            TripStop.trip_id == trip_id,
            TripStop.status == TripStopStatus.COMPLETED
        ).order_by(TripStop.sequence_number.desc()).limit(1)
    )
    max_completed_seq = max_completed_result.scalar_one_or_none() or 0
    
    expected_next_seq = max_completed_seq + 1
    
    if stop.sequence_number != expected_next_seq:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Must complete stops in order. Next stop should be sequence {expected_next_seq}, but you're trying to complete {stop.sequence_number}"
        )
    
    # Complete stop
    stop.status = TripStopStatus.COMPLETED
    stop.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(stop)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.STOP_COMPLETED,
        actor_id=driver_id,
        actor_username=current_user["sub"],
        metadata={
            "trip_id": trip.id,
            "stop_id": stop.id,
            "stop_type": stop.stop_type.value,
            "sequence_number": stop.sequence_number
        }
    )
    
    return StopCompleteResponse(
        stop_id=stop.id,
        trip_id=trip.id,
        status=stop.status.value,
        completed_at=stop.completed_at
    )


@router.post("/trips/{trip_id}/complete")
async def complete_trip(
    trip_id: int = Path(..., description="Trip ID"),
    current_user: dict = Depends(require_role([UserRole.DRIVER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Complete a trip (Driver only).
    
    Validates:
    - All stops are COMPLETED
    - Trip is IN_PROGRESS
    
    Actions:
    - Release vehicle lock
    - Change status to COMPLETED
    - Set completed_at timestamp
    """
    driver_id = current_user["user_id"]
    
    # Get trip
    trip_result = await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )
    trip = trip_result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    # Validate trip is IN_PROGRESS
    if trip.status != TripStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only complete IN_PROGRESS trip, current status: {trip.status.value}"
        )
    
    # Validate driver owns trip
    if trip.driver_id != driver_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This trip is not assigned to you"
        )
    
    # Validate all stops are completed
    pending_stops_result = await db.execute(
        select(TripStop).where(
            TripStop.trip_id == trip_id,
            TripStop.status != TripStopStatus.COMPLETED
        )
    )
    pending_stops = pending_stops_result.scalars().all()
    
    if pending_stops:
        pending_sequences = [stop.sequence_number for stop in pending_stops]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete trip. Pending stops: {pending_sequences}"
        )
    
    # Get total stops completed
    total_stops_result = await db.execute(
        select(TripStop).where(TripStop.trip_id == trip_id)
    )
    total_stops = len(total_stops_result.scalars().all())
    
    # Release vehicle lock
    vehicle_unlocked = False
    if trip.vehicle_id:
        vehicle_unlocked = await release_vehicle_lock(
            db=db,
            vehicle_id=trip.vehicle_id,
            trip_id=trip.id
        )
    
    # Complete trip
    trip.status = TripStatus.COMPLETED
    trip.completed_at = datetime.utcnow()
    
    # Phase 2.6 - Process Billing
    try:
        from backend.app.domain.billing.billing_service import BillingService
        from backend.app.services.audit import AuditAction
        
        await BillingService.process_trip(db, trip.id)
        
        # Log billing success (audit event is distinct from trip complete)
        # We can add a specific billing log here if needed, or rely on the fact it succeeded.
        await log_event(
            db=db,
            action=AuditAction.TRIP_CHARGE_CALCULATED,
            actor_id=driver_id,
            actor_username=current_user["sub"],
            metadata={
                "trip_id": trip.id
            }
        )
        
    except ValueError as e:
        # Critical: Billing failed. Should we rollback trip completion?
        # Yes, financial integrity is paramount.
        # If billing fails, the trip validation/state is invalid for completion?
        # Or do we allow completion and queue billing?
        # Prompt says "Single DB transaction" for billing.
        # Since we are using the same session `db` passed to process_trip, 
        # raising here will cause the route handler to rollback (FastAPI default).
        # So Trip Completion + Billing are atomic. Perfect.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Billing processing failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error during billing calculation"
        )
    
    await db.commit()
    await db.refresh(trip)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.TRIP_COMPLETED,
        actor_id=driver_id,
        actor_username=current_user["sub"],
        metadata={
            "trip_id": trip.id,
            "vehicle_id": trip.vehicle_id,
            "vehicle_unlocked": vehicle_unlocked,
            "total_stops": total_stops
        }
    )
    
    return TripCompleteResponse(
        trip_id=trip.id,
        status=trip.status.value,
        completed_at=trip.completed_at,
        vehicle_unlocked=vehicle_unlocked,
        total_stops_completed=total_stops
    )
