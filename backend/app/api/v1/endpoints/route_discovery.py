"""
Route Discovery API Endpoints - Phase 2.3.2.

Hub Owners discover routes for parcels using ML-powered suggestions.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date

from backend.app.db.session import get_db
from backend.app.models.parcel import Parcel
from backend.app.models.hub import Hub
from backend.app.models.fleet_route import FleetRoute
from backend.app.models.fleet_vehicle import FleetVehicle
from backend.app.models.hub_route_request import HubRouteRequest
from backend.app.models.route_enums import RouteStatus, RouteRequestStatus
from backend.app.schemas.route_discovery import (
    RouteSuggestionsResponse, RouteSuggestion, 
    RouteSuggestionExplainability, RouteRequestResponse
)
from backend.app.schemas.fleet_route import FleetRouteResponse
from backend.app.core.guards import require_role, OwnershipGuard
from backend.app.models.enums import UserRole
from backend.app.services.audit import log_event, AuditAction
from backend.app.services.ml_scoring import score_route_for_parcel

router = APIRouter(prefix="/hub-owner", tags=["Hub Owner - Route Discovery"])
ownership_guard = OwnershipGuard()


@router.get("/parcels/{parcel_id}/route-suggestions")
async def get_route_suggestions(
    parcel_id: int,
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Get ML-powered route suggestions for a parcel.
    
    Returns ranked routes with ML scores, explainability, and fallback to static scoring.
    Vehicle capacity is used as the authoritative source.
    """
    # Get parcel and validate ownership
    parcel_result = await db.execute(
        select(Parcel).where(Parcel.id == parcel_id, Parcel.is_active == True)
    )
    parcel = parcel_result.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found"
        )
    
    # Enforce ownership (parcel must belong to current hub owner)
    ownership_guard.enforce(parcel.hub_owner_id, current_user, "parcel")
    
    # Get parcel's hub for geolocation
    hub_result = await db.execute(
        select(Hub).where(Hub.id == parcel.hub_id)
    )
    hub = hub_result.scalar_one_or_none()
    
    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hub not found for parcel"
        )
    
    # Calculate parcel volume
    parcel_volume_cm3 = parcel.length_cm * parcel.width_cm * parcel.height_cm
    
    # Calculate days until delivery
    days_until_delivery = (parcel.delivery_due_date - date.today()).days
    
    # Get all active routes
    routes_result = await db.execute(
        select(FleetRoute).where(FleetRoute.status == RouteStatus.ACTIVE)
    )
    all_routes = routes_result.scalars().all()
    
    suggestions = []
    ml_enabled = False
    model_version = None
    
    for route in all_routes:
        # Get route capacity from vehicle if assigned
        if route.vehicle_id:
            vehicle_result = await db.execute(
                select(FleetVehicle).where(
                    FleetVehicle.id == route.vehicle_id,
                    FleetVehicle.is_active == True
                )
            )
            vehicle = vehicle_result.scalar_one_or_none()
            
            if vehicle:
                # Use vehicle capacity (authoritative source)
                route_max_weight = vehicle.max_weight_kg
                route_max_volume = vehicle.max_volume_cm3
            else:
                # Skip routes with inactive vehicles
                continue
        else:
            # Use route's capacity if no vehicle assigned (fallback)
            route_max_weight = route.max_weight_kg
            route_max_volume = route.max_volume_cm3
        
        # Score this route for the parcel
        score_result = await score_route_for_parcel(
            db=db,
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
        
        # Track ML status
        if score_result["method"] == "ml":
            ml_enabled = True
            model_version = score_result["model_version"]
        
        # Create suggestion
        explainability = RouteSuggestionExplainability(
            distance_contribution=score_result["explainability"].get("distance_score", 0.0),
            weight_contribution=score_result["explainability"].get("weight_score", 0.0),
            volume_contribution=score_result["explainability"].get("volume_score", 0.0),
            window_contribution=score_result["explainability"].get("window_score", 0.0)
        )
        
        suggestion = RouteSuggestion(
            route=FleetRouteResponse.model_validate(route),
            ml_score=score_result["score"],
            scoring_method=score_result["method"],
            explainability=explainability,
            raw_features=score_result["features"]
        )
        
        suggestions.append(suggestion)
    
    # Sort by ML score (descending)
    suggestions.sort(key=lambda x: x.ml_score, reverse=True)
    
    # Take top 10
    top_suggestions = suggestions[:10]
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.ROUTE_MATCH_SUGGESTED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "parcel_id": parcel_id,
            "total_routes_evaluated": len(all_routes),
            "suggestions_returned": len(top_suggestions),
            "ml_enabled": ml_enabled
        }
    )
    
    return RouteSuggestionsResponse(
        parcel_id=parcel_id,
        suggestions=top_suggestions,
        total_routes_evaluated=len(all_routes),
        ml_enabled=ml_enabled,
        model_version=model_version
    )


@router.post("/routes/{route_id}/request", status_code=status.HTTP_201_CREATED)
async def create_route_request(
    route_id: int,
    parcel_id: int = Query(..., description="Parcel ID"),
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a route request for a specific parcel and route.
    
    This is advisory only - NO auto-assignment happens.
    Hub Owner expresses interest in a route for their parcel.
    """
    # Get and validate parcel ownership
    parcel_result = await db.execute(
        select(Parcel).where(Parcel.id == parcel_id, Parcel.is_active == True)
    )
    parcel = parcel_result.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found"
        )
    
    ownership_guard.enforce(parcel.hub_owner_id, current_user, "parcel")
    
    # Validate route exists and is active
    route_result = await db.execute(
        select(FleetRoute).where(FleetRoute.id == route_id, FleetRoute.status == RouteStatus.ACTIVE)
    )
    route = route_result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found or inactive"
        )
    
    # Check if request already exists (one request per parcel per route)
    existing_request = await db.execute(
        select(HubRouteRequest).where(
            HubRouteRequest.parcel_id == parcel_id,
            HubRouteRequest.route_id == route_id
        )
    )
    if existing_request.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request already exists for this parcel and route"
        )
    
    # Create route request
    route_request = HubRouteRequest(
        hub_id=parcel.hub_id,
        parcel_id=parcel_id,
        route_id=route_id,
        hub_owner_id=current_user["user_id"],
        status=RouteRequestStatus.PENDING
    )
    
    db.add(route_request)
    await db.commit()
    await db.refresh(route_request)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.HUB_ROUTE_REQUESTED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "request_id": route_request.id,
            "parcel_id": parcel_id,
            "route_id": route_id,
            "hub_id": parcel.hub_id
        }
    )
    
    return RouteRequestResponse(
        id=route_request.id,
        hub_id=route_request.hub_id,
        parcel_id=route_request.parcel_id,
        route_id=route_request.route_id,
        hub_owner_id=route_request.hub_owner_id,
        status=route_request.status.value,
        requested_at=route_request.requested_at.isoformat()
    )
