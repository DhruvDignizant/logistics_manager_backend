"""
Trip Creation API Endpoints - Phase 2.4.1.

Fleet Owners explicitly create trips from accepted route requests.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.db.session import get_db
from backend.app.models.hub_route_request import HubRouteRequest
from backend.app.models.route_request_trip_map import RouteRequestTripMap
from backend.app.models.fleet_route import FleetRoute
from backend.app.models.fleet_vehicle import FleetVehicle
from backend.app.models.parcel import Parcel
from backend.app.models.hub import Hub
from backend.app.models.trip import Trip
from backend.app.models.trip_stop import TripStop
from backend.app.models.route_enums import RouteRequestStatus
from backend.app.models.trip_enums import TripStatus, TripStopType, TripStopStatus
from backend.app.schemas.trip import TripResponse, TripStopResponse, TripCreateResponse, TripListResponse
from backend.app.core.guards import require_role, OwnershipGuard
from backend.app.models.enums import UserRole
from backend.app.services.audit import log_event, AuditAction

router = APIRouter(prefix="/fleet-owner", tags=["Fleet Owner - Trips"])
ownership_guard = OwnershipGuard()


@router.post("/route-requests/{request_id}/create-trip", status_code=status.HTTP_201_CREATED)
async def create_trip_from_request(
    request_id: int = Path(..., description="Route Request ID"),
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a trip from an accepted route request (Fleet Owner only).
    
    Validates:
    - Request is ACCEPTED
    - Request belongs to Fleet Owner's route
    - Vehicle capacity can accommodate parcel
    - No trip already exists for this request (idempotency)
    
    Generates:
    - Trip in PLANNED status
    - Pickup stop (from hub)
    - Delivery stop (to route destination)
    """
    # Get route request
    request_result = await db.execute(
        select(HubRouteRequest).where(HubRouteRequest.id == request_id)
    )
    route_request = request_result.scalar_one_or_none()
    
    if not route_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route request not found"
        )
    
    # Validate request is ACCEPTED
    if route_request.status != RouteRequestStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only create trip from ACCEPTED request, current status: {route_request.status.value}"
        )
    
    # Get route and validate ownership
    route_result = await db.execute(
        select(FleetRoute).where(FleetRoute.id == route_request.route_id)
    )
    route = route_result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    ownership_guard.enforce(route.fleet_owner_id, current_user, "route")
    
    # Check idempotency: trip already exists for this request?
    existing_map = await db.execute(
        select(RouteRequestTripMap).where(RouteRequestTripMap.route_request_id == request_id)
    )
    if existing_map.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trip already exists for this route request"
        )
    
    # Get parcel
    parcel_result = await db.execute(
        select(Parcel).where(Parcel.id == route_request.parcel_id)
    )
    parcel = parcel_result.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found"
        )
    
    # Get hub for pickup location
    hub_result = await db.execute(
        select(Hub).where(Hub.id == route_request.hub_id)
    )
    hub = hub_result.scalar_one_or_none()
    
    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hub not found"
        )
    
    # Validate vehicle capacity if vehicle assigned to route
    capacity_validated = False
    vehicle_id = None
    
    if route.vehicle_id:
        vehicle_result = await db.execute(
            select(FleetVehicle).where(
                FleetVehicle.id == route.vehicle_id,
                FleetVehicle.is_active == True
            )
        )
        vehicle = vehicle_result.scalar_one_or_none()
        
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Route vehicle not found or inactive"
            )
        
        # Calculate parcel dimensions
        parcel_volume_cm3 = parcel.length_cm * parcel.width_cm * parcel.height_cm
        
        # Validate capacity
        if parcel.weight_kg > vehicle.max_weight_kg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parcel weight ({parcel.weight_kg}kg) exceeds vehicle capacity ({vehicle.max_weight_kg}kg)"
            )
        
        if parcel_volume_cm3 > vehicle.max_volume_cm3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parcel volume ({parcel_volume_cm3}cm³) exceeds vehicle capacity ({vehicle.max_volume_cm3}cm³)"
            )
        
        capacity_validated = True
        vehicle_id = vehicle.id
    
    # Create trip
    new_trip = Trip(
        fleet_owner_id=current_user["user_id"],
        route_id=route.id,
        vehicle_id=vehicle_id,
        driver_id=None,  # No driver assignment in Phase 2.4.1
        status=TripStatus.PLANNED
    )
    
    db.add(new_trip)
    await db.flush()  # Get trip ID
    
    # Create trip stops
    stops_created = 0
    
    # Stop 1: PICKUP from hub
    pickup_stop = TripStop(
        trip_id=new_trip.id,
        parcel_id=parcel.id,
        stop_type=TripStopType.PICKUP,
        sequence_number=1,
        location_lat=hub.latitude or 0.0,
        location_lng=hub.longitude or 0.0,
        location_address=hub.address,
        status=TripStopStatus.PENDING
    )
    db.add(pickup_stop)
    stops_created += 1
    
    # Stop 2: DELIVERY to route destination
    delivery_stop = TripStop(
        trip_id=new_trip.id,
        parcel_id=parcel.id,
        stop_type=TripStopType.DELIVERY,
        sequence_number=2,
        location_lat=route.destination_lat,
        location_lng=route.destination_lng,
        location_address=route.destination_address,
        status=TripStopStatus.PENDING
    )
    db.add(delivery_stop)
    stops_created += 1
    
    # Create mapping for idempotency
    trip_map = RouteRequestTripMap(
        route_request_id=request_id,
        trip_id=new_trip.id
    )
    db.add(trip_map)
    
    await db.commit()
    await db.refresh(new_trip)
    await db.refresh(pickup_stop)
    await db.refresh(delivery_stop)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.TRIP_CREATED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "trip_id": new_trip.id,
            "route_request_id": request_id,
            "route_id": route.id,
            "parcel_id": parcel.id,
            "vehicle_id": vehicle_id,
            "capacity_validated": capacity_validated,
            "stops_generated": stops_created
        }
    )
    
    # Build response
    trip_response = TripResponse(
        id=new_trip.id,
        fleet_owner_id=new_trip.fleet_owner_id,
        route_id=new_trip.route_id,
        vehicle_id=new_trip.vehicle_id,
        driver_id=new_trip.driver_id,
        status=new_trip.status.value,
        created_at=new_trip.created_at,
        updated_at=new_trip.updated_at,
        started_at=new_trip.started_at,
        completed_at=new_trip.completed_at,
        stops=[
            TripStopResponse.model_validate(pickup_stop),
            TripStopResponse.model_validate(delivery_stop)
        ]
    )
    
    return TripCreateResponse(
        trip=trip_response,
        route_request_id=request_id,
        capacity_validated=capacity_validated,
        stops_generated=stops_created
    )


@router.get("/trips")
async def list_own_trips(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    List all trips owned by the Fleet Owner.
    """
    user_id = current_user["user_id"]
    
    # Get total count
    count_query = select(func.count(Trip.id)).where(
        Trip.fleet_owner_id == user_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated trips
    offset = (page - 1) * page_size
    query = select(Trip).where(
        Trip.fleet_owner_id == user_id
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
