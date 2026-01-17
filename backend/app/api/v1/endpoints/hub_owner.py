"""
Hub Owner API Endpoints - Phase 2.1.

Allows Hub Owners to create and manage their hubs with strict ownership enforcement.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.app.db.session import get_db
from backend.app.models.hub import Hub
from backend.app.models.user import User
from backend.app.schemas.hub import HubCreate, HubUpdate, HubResponse, HubListResponse
from backend.app.core.guards import require_role, OwnershipGuard
from backend.app.core.dependencies import get_current_user
from backend.app.models.enums import UserRole
from backend.app.services.audit import log_event, AuditAction

router = APIRouter(prefix="/hub-owner", tags=["Hub Owner"])
ownership_guard = OwnershipGuard()


@router.post("/hubs", response_model=HubResponse, status_code=status.HTTP_201_CREATED)
async def create_hub(
    hub_data: HubCreate,
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new hub (Hub Owner only).
    
    Hub is automatically assigned to the authenticated Hub Owner.
    """
    # Create hub owned by current user
    new_hub = Hub(
        hub_owner_id=current_user["user_id"],
        name=hub_data.name,
        address=hub_data.address,
        city=hub_data.city,
        state=hub_data.state,
        country=hub_data.country,
        pincode=hub_data.pincode,
        latitude=hub_data.latitude,
        longitude=hub_data.longitude,
        is_active=True
    )
    
    db.add(new_hub)
    await db.commit()
    await db.refresh(new_hub)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.HUB_CREATED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "hub_id": new_hub.id,
            "hub_name": new_hub.name,
            "city": new_hub.city
        }
    )
    
    return HubResponse.model_validate(new_hub)


@router.get("/hubs", response_model=HubListResponse)
async def list_own_hubs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    List all hubs owned by the authenticated Hub Owner.
    
    Only shows hubs belonging to the current user (ownership enforced).
    """
    user_id = current_user["user_id"]
    
    # Get total count (only own hubs)
    count_query = select(func.count(Hub.id)).where(
        Hub.hub_owner_id == user_id,
        Hub.is_active == True
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated hubs (only own hubs)
    offset = (page - 1) * page_size
    query = select(Hub).where(
        Hub.hub_owner_id == user_id,
        Hub.is_active == True
    ).order_by(Hub.created_at.desc()).offset(offset).limit(page_size)
    
    result = await db.execute(query)
    hubs = result.scalars().all()
    
    return HubListResponse(
        hubs=[HubResponse.model_validate(hub) for hub in hubs],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/hubs/{hub_id}", response_model=HubResponse)
async def get_hub(
    hub_id: int,
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific hub (Hub Owner only).
    
    Ownership is enforced - can only view own hubs.
    """
    result = await db.execute(
        select(Hub).where(Hub.id == hub_id, Hub.is_active == True)
    )
    hub = result.scalar_one_or_none()
    
    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hub not found"
        )
    
    # Enforce ownership
    ownership_guard.enforce(hub.hub_owner_id, current_user, "hub")
    
    return HubResponse.model_validate(hub)


@router.patch("/hubs/{hub_id}", response_model=HubResponse)
async def update_hub(
    hub_id: int,
    hub_data: HubUpdate,
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Update hub details (Hub Owner only).
    
    Can only update own hubs (ownership enforced).
    """
    result = await db.execute(
        select(Hub).where(Hub.id == hub_id, Hub.is_active == True)
    )
    hub = result.scalar_one_or_none()
    
    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hub not found"
        )
    
    # Enforce ownership
    ownership_guard.enforce(hub.hub_owner_id, current_user, "hub")
    
    # Update fields (only if provided)
    update_data = hub_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(hub, field, value)
    
    await db.commit()
    await db.refresh(hub)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.HUB_UPDATED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "hub_id": hub.id,
            "hub_name": hub.name,
            "updated_fields": list(update_data.keys())
        }
    )
    
    return HubResponse.model_validate(hub)


@router.patch("/hubs/{hub_id}/deactivate", response_model=HubResponse)
async def deactivate_hub(
    hub_id: int,
    current_user: dict = Depends(require_role([UserRole.HUB_OWNER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a hub (soft delete) - Hub Owner only.
    
    Can only deactivate own hubs (ownership enforced).
    """
    result = await db.execute(
        select(Hub).where(Hub.id == hub_id, Hub.is_active == True)
    )
    hub = result.scalar_one_or_none()
    
    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hub not found or already deactivated"
        )
    
    # Enforce ownership
    ownership_guard.enforce(hub.hub_owner_id, current_user, "hub")
    
    # Soft delete
    hub.is_active = False
    await db.commit()
    await db.refresh(hub)
    
    # Audit log
    await log_event(
        db=db,
        action=AuditAction.HUB_DEACTIVATED,
        actor_id=current_user["user_id"],
        actor_username=current_user["sub"],
        metadata={
            "hub_id": hub.id,
            "hub_name": hub.name
        }
    )
    
    return HubResponse.model_validate(hub)
