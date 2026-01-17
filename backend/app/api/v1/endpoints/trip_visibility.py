"""
Hub Owner Trip Visibility - Phase 2.4.1.

Hub Owners can view trip status for their parcels.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.models.parcel import Parcel
from backend.app.models.trip import Trip
from backend.app.models.trip_stop import TripStop
from backend.app.schemas.trip import TripResponse, TripStopResponse
from backend.app.core.guards import require_role, OwnershipGuard
from backend.app.models.enums import UserRole

router = APIRouter(prefix="/hub-owner", tags=["Hub Owner - Trip Visibility"])
ownership_guard = OwnershipGuard()


@router.get("/parcels/{parcel_id}/trip")
async def get_parcel_trip(
    parcel_id: int = Path(..., description="Parcel ID"),
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Get trip information for a parcel (Hub Owner only).
    
    Returns trip and stop details if trip exists for this parcel.
    """
    # Get parcel and validate ownership
    parcel_result = await db.execute(
        select(Parcel).where(Parcel.id == parcel_id)
    )
    parcel = parcel_result.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found"
        )
    
    ownership_guard.enforce(parcel.hub_owner_id, current_user, "parcel")
    
    # Find trip via stops
    stop_result = await db.execute(
        select(TripStop).where(TripStop.parcel_id == parcel_id)
    )
    stop = stop_result.scalar_one_or_none()
    
    if not stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No trip found for this parcel"
        )
    
    # Get trip
    trip_result = await db.execute(
        select(Trip).where(Trip.id == stop.trip_id)
    )
    trip = trip_result.scalar_one_or_none()
    
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    # Get all stops for trip
    stops_result = await db.execute(
        select(TripStop).where(TripStop.trip_id == trip.id).order_by(TripStop.sequence_number)
    )
    stops = stops_result.scalars().all()
    
    return TripResponse(
        id=trip.id,
        fleet_owner_id=trip.fleet_owner_id,
        route_id=trip.route_id,
        vehicle_id=trip.vehicle_id,
        driver_id=trip.driver_id,
        status=trip.status.value,
        created_at=trip.created_at,
        updated_at=trip.updated_at,
        started_at=trip.started_at,
        completed_at=trip.completed_at,
        stops=[TripStopResponse.model_validate(s) for s in stops]
    )
