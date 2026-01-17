"""
Route connectivity validation service for Phase 2.4.2.

Validates if routes are "connected" to allow multiple driver assignments.
"""

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.trip import Trip
from backend.app.models.fleet_route import FleetRoute
from backend.app.services.ml_features import haversine_distance


# Configuration
CONNECTIVITY_DISTANCE_THRESHOLD_KM = 50  # Destination within 50km of next origin
CONNECTIVITY_DATE_THRESHOLD_DAYS = 2  # Trips within 2 days


async def validate_route_connectivity(
    db: AsyncSession,
    existing_trip: Trip,
    new_trip: Trip
) -> bool:
    """
    Validate if two trips have connected routes.
    
    Routes are considered connected if:
    1. Same route (route_id matches)
    2. Destination of first near origin of second (<50km)
    3. Sequential timing (created within 2 days)
    
    Args:
        db: Database session
        existing_trip: Existing assigned trip
        new_trip: New trip to assign
    
    Returns:
        True if routes are connected, False otherwise
    """
    # Get routes
    existing_route_result = await db.execute(
        select(FleetRoute).where(FleetRoute.id == existing_trip.route_id)
    )
    existing_route = existing_route_result.scalar_one_or_none()
    
    new_route_result = await db.execute(
        select(FleetRoute).where(FleetRoute.id == new_trip.route_id)
    )
    new_route = new_route_result.scalar_one_or_none()
    
    if not existing_route or not new_route:
        return False
    
    # Rule 1: Same route
    if existing_route.id == new_route.id:
        return True
    
    # Rule 2: Destination of existing route near origin of new route
    distance_km = haversine_distance(
        existing_route.destination_lat,
        existing_route.destination_lng,
        new_route.origin_lat,
        new_route.origin_lng
    )
    
    if distance_km <= CONNECTIVITY_DISTANCE_THRESHOLD_KM:
        # Also check timing (Rule 3)
        time_diff = abs((new_trip.created_at - existing_trip.created_at).days)
        if time_diff <= CONNECTIVITY_DATE_THRESHOLD_DAYS:
            return True
    
    return False


async def can_assign_driver_to_trip(
    db: AsyncSession,
    driver_id: int,
    new_trip: Trip
) -> tuple[bool, str]:
    """
    Check if a driver can be assigned to a new trip.
    
    Allows multiple PLANNED trips only if routes are connected.
    
    Args:
        db: Database session
        driver_id: Driver user ID
        new_trip: Trip to assign driver to
    
    Returns:
        (can_assign: bool, reason: str)
    """
    # Get all PLANNED trips assigned to this driver
    existing_trips_result = await db.execute(
        select(Trip).where(
            Trip.driver_id == driver_id,
            Trip.status == "PLANNED"
        )
    )
    existing_trips = existing_trips_result.scalars().all()
    
    # If no existing trips, assignment is allowed
    if not existing_trips:
        return True, "No conflicts"
    
    # Check connectivity with all existing trips
    for existing_trip in existing_trips:
        is_connected = await validate_route_connectivity(db, existing_trip, new_trip)
        if not is_connected:
            return False, f"Route not connected to existing trip {existing_trip.id}"
    
    return True, "All routes connected"
