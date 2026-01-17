"""
Route Request Decision API Endpoints - Phase 2.3.3.

Fleet Owners can accept or reject route requests, feeding ML training pipeline.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from backend.app.db.session import get_db
from backend.app.models.hub_route_request import HubRouteRequest
from backend.app.models.fleet_route import FleetRoute
from backend.app.models.route_enums import RouteRequestStatus
from backend.app.schemas.route_request_decision import (
    RouteRequestAccept, RouteRequestReject, RouteRequestDecisionResponse
)
from backend.app.schemas.route_discovery import RouteRequestResponse, RouteRequestListResponse
from backend.app.core.guards import require_role, OwnershipGuard
from backend.app.models.enums import UserRole
from backend.app.services.audit import log_event, AuditAction
from backend.app.services.ml_feedback import create_ml_feedback_from_decision

router = APIRouter(prefix="/fleet-owner", tags=["Fleet Owner - Route Request Decisions"])
ownership_guard = OwnershipGuard()


@router.post("/route-requests/{request_id}/accept", status_code=status.HTTP_200_OK)
async def accept_route_request(
    request_id: int = Path(..., description="Route Request ID"),
    accept_data: RouteRequestAccept = ...,
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Accept a route request (Fleet Owner only).
    
    This is advisory only - NO trip creation, NO driver assignment.
    Decision is immutable once made.
    Creates ML training data with label=1 (successful match).
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
    
    # Validate route ownership
    route_result = await db.execute(
        select(FleetRoute).where(FleetRoute.id == route_request.route_id)
    )
    route = route_result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    # Enforce ownership (request must be for Fleet Owner's route)
    ownership_guard.enforce(route.fleet_owner_id, current_user, "route")
    
    # Check if already decided (immutability)
    if route_request.status != RouteRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request already decided with status: {route_request.status.value}"
        )
    
    # Accept request
    route_request.status = RouteRequestStatus.ACCEPTED
    route_request.decided_at = datetime.utcnow()
    
    # Create ML training data (was_successful = True)
    ml_training_recorded = False
    try:
        await create_ml_feedback_from_decision(
            db=db,
            request=route_request,
            was_accepted=True
        )
        ml_training_recorded = True
    except Exception as e:
        # Log error but don't fail the acceptance
        print(f"Failed to create ML feedback: {e}")
    
    await db.commit()
    await db.refresh(route_request)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.HUB_ROUTE_ACCEPTED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "request_id": route_request.id,
            "route_id": route_request.route_id,
            "parcel_id": route_request.parcel_id,
            "hub_owner_id": route_request.hub_owner_id,
            "ml_training_recorded": ml_training_recorded
        }
    )
    
    return RouteRequestDecisionResponse(
        id=route_request.id,
        status=route_request.status.value,
        decision_reason=route_request.decision_reason,
        decided_at=route_request.decided_at.isoformat(),
        ml_training_recorded=ml_training_recorded
    )


@router.post("/route-requests/{request_id}/reject", status_code=status.HTTP_200_OK)
async def reject_route_request(
    request_id: int = Path(..., description="Route Request ID"),
    reject_data: RouteRequestReject = ...,
    current_user: dict = Depends(require_role([UserRole.FLEET_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Reject a route request (Fleet Owner only).
    
    Requires a reason for rejection.
    Decision is immutable once made.
    Creates ML training data with label=0 (unsuccessful match).
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
    
    # Validate route ownership
    route_result = await db.execute(
        select(FleetRoute).where(FleetRoute.id == route_request.route_id)
    )
    route = route_result.scalar_one_or_none()
    
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found"
        )
    
    # Enforce ownership (request must be for Fleet Owner's route)
    ownership_guard.enforce(route.fleet_owner_id, current_user, "route")
    
    # Check if already decided (immutability)
    if route_request.status != RouteRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request already decided with status: {route_request.status.value}"
        )
    
    # Reject request
    route_request.status = RouteRequestStatus.REJECTED
    route_request.decision_reason = reject_data.reason
    route_request.decided_at = datetime.utcnow()
    
    # Create ML training data (was_successful = False)
    ml_training_recorded = False
    try:
        await create_ml_feedback_from_decision(
            db=db,
            request=route_request,
            was_accepted=False
        )
        ml_training_recorded = True
    except Exception as e:
        # Log error but don't fail the rejection
        print(f"Failed to create ML feedback: {e}")
    
    await db.commit()
    await db.refresh(route_request)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.HUB_ROUTE_REJECTED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "request_id": route_request.id,
            "route_id": route_request.route_id,
            "parcel_id": route_request.parcel_id,
            "hub_owner_id": route_request.hub_owner_id,
            "rejection_reason": reject_data.reason,
            "ml_training_recorded": ml_training_recorded
        }
    )
    
    return RouteRequestDecisionResponse(
        id=route_request.id,
        status=route_request.status.value,
        decision_reason=route_request.decision_reason,
        decided_at=route_request.decided_at.isoformat(),
        ml_training_recorded=ml_training_recorded
    )


# Hub Owner endpoint to view their own route requests
@router.get("/hub-owner/route-requests")
async def list_hub_owner_route_requests(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    List all route requests made by the Hub Owner.
    
    Shows status of requests (PENDING, ACCEPTED, REJECTED).
    """
    user_id = current_user["user_id"]
    
    # Get total count
    count_query = select(func.count(HubRouteRequest.id)).where(
        HubRouteRequest.hub_owner_id == user_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated requests
    offset = (page - 1) * page_size
    query = select(HubRouteRequest).where(
        HubRouteRequest.hub_owner_id == user_id
    ).order_by(HubRouteRequest.requested_at.desc()).offset(offset).limit(page_size)
    
    request_result = await db.execute(query)
    requests = request_result.scalars().all()
    
    return RouteRequestListResponse(
        requests=[
            RouteRequestResponse(
                id=req.id,
                hub_id=req.hub_id,
                parcel_id=req.parcel_id,
                route_id=req.route_id,
                hub_owner_id=req.hub_owner_id,
                status=req.status.value,
                requested_at=req.requested_at.isoformat()
            ) for req in requests
        ],
        total=total,
        page=page,
        page_size=page_size
    )
