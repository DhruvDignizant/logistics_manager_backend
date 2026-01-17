"""
Fleet Owner Route API Endpoints - Phase 2.3.1.

Allows Fleet Owners to create and manage their routes with strict ownership enforcement.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db.session import get_db
from backend.app.models.fleet_route import FleetRoute
from backend.app.models.route_enums import RouteStatus
from backend.app.schemas.fleet_route import FleetRouteCreate, FleetRouteUpdate, FleetRouteResponse, FleetRouteListResponse
from backend.app.core.guards import require_role, OwnershipGuard
from backend.app.core.dependencies import get_current_user
from backend.app.models.enums import UserRole
from backend.app.services.audit import log_event, AuditAction

router = APIRouter(prefix="/fleet-owner", tags=["Fleet Owner - Routes"])
ownership_guard = OwnershipGuard()


@router.post("/routes", response_model=FleetRouteResponse, status_code=status.HTTP_201_CREATED)
async def create_route(
    route_data: FleetRouteCreate,
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new fleet route (Fleet Owner only).
    
    Route is automatically assigned to the authenticated Fleet Owner.
    """
    # Create route owned by current user
    new_route = FleetRoute(
        fleet_owner_id=current_user["user_id"],
        route_name=route_data.route_name,
        origin_lat=route_data.origin_lat,
        origin_lng=route_data.origin_lng,
        origin_address=route_data.origin_address,
        destination_lat=route_data.destination_lat,
        destination_lng=route_data.destination_lng,
        destination_address=route_data.destination_address,
        max_weight_kg=route_data.max_weight_kg,
        max_volume_cm3=route_data.max_volume_cm3,
        status=RouteStatus.ACTIVE
    )
    
    db.add(new_route)
    await db.commit()
    await db.refresh(new_route)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.ROUTE_CREATED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "route_id": new_route.id,
            "route_name": new_route.route_name,
            "max_weight_kg": new_route.max_weight_kg
        }
    )
    
    return FleetRouteResponse.model_validate(new_route)


@router.get("/routes", response_model=FleetRouteListResponse)
async def list_own_routes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    List all routes owned by the authenticated Fleet Owner.
    
    Only shows routes belonging to the current user (ownership enforced).
    """
    user_id = current_user["user_id"]
    
    # Get total count (only own routes)
    count_query = select(func.count(FleetRoute.id)).where(
        FleetRoute.fleet_owner_id == user_id,
        FleetRoute.status == RouteStatus.ACTIVE
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated routes (only own routes)
    offset = (page - 1) * page_size
    query = select(FleetRoute).where(
        FleetRoute.fleet_owner_id == user_id,
        FleetRoute.status == RouteStatus.ACTIVE
    ).order_by(FleetRoute.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    routes = result.scalars().all()
    
    return FleetRouteListResponse(
        routes=[FleetRouteResponse.model_validate(route) for route in routes],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/routes/{route_id}", response_model=FleetRouteResponse)
async def get_route(
    route_id: int = Path(..., description="Route ID"),
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific route (Fleet Owner only).
    
    Ownership is enforced - can only view own routes.
    """
    result = await db.execute(
        select(FleetRoute).where(FleetRoute.id == route_id, FleetRoute.status == RouteStatus.ACTIVE)
    )
    route = result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    # Enforce ownership
    ownership_guard.enforce(route.fleet_owner_id, current_user, "route")
    
    return FleetRouteResponse.model_validate(route)


@router.patch("/routes/{route_id}", response_model=FleetRouteResponse)
async def update_route(
    route_id: int = Path(..., description="Route ID"),
    route_data: FleetRouteUpdate = ...,
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Update route details (Fleet Owner only).
    
    Can only update own routes (ownership enforced).
    """
    result = await db.execute(
        select(FleetRoute).where(FleetRoute.id == route_id, FleetRoute.status == RouteStatus.ACTIVE)
    )
    route = result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    # Enforce ownership
    ownership_guard.enforce(route.fleet_owner_id, current_user, "route")
    
    # Update fields (only if provided)
    update_data = route_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(route, field, value)
    
    await db.commit()
    await db.refresh(route)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.ROUTE_UPDATED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "route_id": route.id,
            "route_name": route.route_name,
            "updated_fields": list(update_data.keys())
        }
    )
    
    return FleetRouteResponse.model_validate(route)


@router.patch("/routes/{route_id}/deactivate", response_model=FleetRouteResponse)
async def deactivate_route(
    route_id: int = Path(..., description="Route ID"),
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a route (soft delete) - Fleet Owner only.
    
    Can only deactivate own routes (ownership enforced).
    """
    result = await db.execute(
        select(FleetRoute).where(FleetRoute.id == route_id, FleetRoute.status == RouteStatus.ACTIVE)
    )
    route = result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found or already deactivated"
        )
    
    # Enforce ownership
    ownership_guard.enforce(route.fleet_owner_id, current_user, "route")
    
    # Soft delete
    route.status = RouteStatus.INACTIVE
    await db.commit()
    await db.refresh(route)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.ROUTE_DEACTIVATED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "route_id": route.id,
            "route_name": route.route_name
        }
    )
    
    return FleetRouteResponse.model_validate(route)
