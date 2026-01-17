"""
Driver Visibility API Endpoints - Phase 2.4.2.

Drivers can view their assigned trips.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.db.session import get_db
from backend.app.models.trip import Trip
from backend.app.models.trip_stop import TripStop
from backend.app.models.enums import UserRole
from backend.app.schemas.trip import TripResponse, TripStopResponse, TripListResponse
from backend.app.core.guards import require_role

router = APIRouter(prefix="/driver", tags=["Driver - Trips"])


@router.get("/trips")
async def list_driver_trips(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_role([UserRole.DRIVER])),
    db: AsyncSession = Depends(get_db)
):
    """
    List all trips assigned to the driver.
    
    Shows PENDING, IN_PROGRESS, and COMPLETED trips.
    """
    driver_id = current_user["user_id"]
    
    # Get total count
    count_query = select(func.count(Trip.id)).where(
        Trip.driver_id == driver_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated trips
    offset = (page - 1) * page_size
    query = select(Trip).where(
        Trip.driver_id == driver_id
    ).order_by(Trip.created_at.desc()).offset(offset).limit(page_size)
    
    trip_result = await db.execute(query)
    trips = trip_result.scalars().all()
    
    # Get stops for each trip
    trip_responses = []
    for trip in trips:
        stops_result = await db.execute(
            select(TripStop).where(TripStop.trip_id == trip.id).order_by(TripStop.sequence_number)
        )
        stops = stops_result.scalars().all()
        
        trip_responses.append(TripResponse(
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
        ))
    
    return TripListResponse(
        trips=trip_responses,
        total=total,
        page=page,
        page_size=page_size
    )
