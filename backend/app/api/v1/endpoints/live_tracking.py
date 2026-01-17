"""
Live Trip Tracking API Endpoints - Phase 2.5.

Fleet Owners and Hub Owners can view live trip tracking.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.db.session import get_db
from backend.app.models.trip import Trip
from backend.app.models.trip_stop import TripStop
from backend.app.models.trip_location import TripLocation
from backend.app.models.parcel import Parcel
from backend.app.models.enums import UserRole
from backend.app.schemas.trip import TripResponse, TripStopResponse
from backend.app.schemas.trip_execution import TripLocationResponse
from backend.app.core.guards import require_role, OwnershipGuard
from typing import List

fleet_router = APIRouter(prefix="/fleet-owner", tags=["Fleet Owner - Live Tracking"])
hub_router = APIRouter(prefix="/hub-owner", tags=["Hub Owner - Live Tracking"])
ownership_guard = OwnershipGuard()


@fleet_router.get("/trips/{trip_id}/live")
async def get_live_trip_tracking(
    trip_id: int = Path(..., description="Trip ID"),
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Get live trip tracking (Fleet Owner only).
    
    Returns trip details with all GPS locations.
    """
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
    
    # Validate ownership
    ownership_guard.enforce(trip.fleet_owner_id, current_user, "trip")
    
    # Get stops
    stops_result = await db.execute(
        select(TripStop).where(TripStop.trip_id == trip_id).order_by(TripStop.sequence_number)
    )
    stops = stops_result.scalars().all()
    
    # Get locations
    locations_result = await db.execute(
        select(TripLocation).where(
            TripLocation.trip_id == trip_id
        ).order_by(TripLocation.recorded_at.desc())
    )
    locations = locations_result.scalars().all()
    
    return {
        "trip": TripResponse(
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
            stops=[TripStopResponse.model_validate(stop) for stop in stops]
        ),
        "locations": [TripLocationResponse.model_validate(loc) for loc in locations],
        "total_locations": len(locations)
    }


@hub_router.get("/parcels/{parcel_id}/tracking")
async def get_parcel_tracking(
    parcel_id: int = Path(..., description="Parcel ID"),
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Get live tracking for a parcel (Hub Owner only).
    
    Returns trip and location data if trip exists for parcel.
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
    
    # Get recent locations (last 50)
    locations_result = await db.execute(
        select(TripLocation).where(
            TripLocation.trip_id == trip.id
        ).order_by(TripLocation.recorded_at.desc()).limit(50)
    )
    locations = locations_result.scalars().all()
    
    return {
        "parcel_id": parcel_id,
        "trip": TripResponse(
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
        ),
        "locations": [TripLocationResponse.model_validate(loc) for loc in locations],
        "location_count": len(locations)
    }
