"""
ML Feedback service for Phase 2.3.3.

Creates training data records from route request decisions.
"""

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.hub_route_request import HubRouteRequest
from backend.app.models.parcel import Parcel
from backend.app.models.hub import Hub
from backend.app.models.fleet_route import FleetRoute
from backend.app.models.fleet_vehicle import FleetVehicle
from backend.app.models.ml_training_data import MLRouteTrainingData
from backend.app.services.ml_features import extract_features


async def create_ml_feedback_from_decision(
    db: AsyncSession,
    request: HubRouteRequest,
    was_accepted: bool
) -> MLRouteTrainingData:
    """
    Create ML training data record from route request decision.
    
    Args:
        db: Database session
        request: The route request with decision
        was_accepted: True if accepted, False if rejected
    
    Returns:
        Created training data record
    """
    # Get parcel
    parcel_result = await db.execute(
        select(Parcel).where(Parcel.id == request.parcel_id)
    )
    parcel = parcel_result.scalar_one_or_none()
    
    if not parcel:
        raise ValueError(f"Parcel {request.parcel_id} not found")
    
    # Get hub for geolocation
    hub_result = await db.execute(
        select(Hub).where(Hub.id == request.hub_id)
    )
    hub = hub_result.scalar_one_or_none()
    
    if not hub:
        raise ValueError(f"Hub {request.hub_id} not found")
    
    # Get route
    route_result = await db.execute(
        select(FleetRoute).where(FleetRoute.id == request.route_id)
    )
    route = route_result.scalar_one_or_none()
    
    if not route:
        raise ValueError(f"Route {request.route_id} not found")
    
    # Get route capacity (from vehicle if assigned)
    if route.vehicle_id:
        vehicle_result = await db.execute(
            select(FleetVehicle).where(FleetVehicle.id == route.vehicle_id)
        )
        vehicle = vehicle_result.scalar_one_or_none()
        
        if vehicle:
            route_max_weight = vehicle.max_weight_kg
            route_max_volume = vehicle.max_volume_cm3
        else:
            route_max_weight = route.max_weight_kg
            route_max_volume = route.max_volume_cm3
    else:
        route_max_weight = route.max_weight_kg
        route_max_volume = route.max_volume_cm3
    
    # Calculate parcel volume
    parcel_volume_cm3 = parcel.length_cm * parcel.width_cm * parcel.height_cm
    
    # Calculate days until delivery
    days_until_delivery = (parcel.delivery_due_date - date.today()).days
    
    # Extract features
    features = extract_features(
        hub_lat=hub.latitude or 0.0,
        hub_lng=hub.longitude or 0.0,
        parcel_weight_kg=parcel.weight_kg,
        parcel_volume_cm3=parcel_volume_cm3,
        parcel_due_days=days_until_delivery,
        route_origin_lat=route.origin_lat,
        route_origin_lng=route.origin_lng,
        route_max_weight_kg=route_max_weight,
        route_max_volume_cm3=route_max_volume
    )
    
    # Create training data record
    training_data = MLRouteTrainingData(
        route_id=request.route_id,
        parcel_id=request.parcel_id,
        distance_score=features["distance_score"],
        weight_score=features["weight_score"],
        volume_score=features["volume_score"],
        window_score=features["window_score"],
        was_successful=was_accepted  # 1 for accepted, 0 for rejected
    )
    
    db.add(training_data)
    await db.flush()
    
    return training_data
